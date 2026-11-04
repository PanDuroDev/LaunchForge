use std::fs;
use std::path::PathBuf;

use launchforge_project::{
    MAX_PROJECT_BYTES, ProjectError, ProjectStore, PROJECT_SCHEMA_VERSION,
};
use serde_json::{Value, json};
use tempfile::tempdir;
use uuid::Uuid;

fn repository_path(relative: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(relative)
}

fn store() -> ProjectStore {
    ProjectStore::with_schema_json(
        &fs::read_to_string(repository_path("poc/contracts/project-v1.schema.json")).unwrap(),
    )
    .unwrap()
}

fn sample_project() -> Value {
    serde_json::from_str(
        &fs::read_to_string(repository_path("poc/fixtures/sample-project.json")).unwrap(),
    )
    .unwrap()
}

fn expect_validation_code(error: ProjectError, expected: &str) {
    match error {
        ProjectError::ValidationFailed { diagnostics, .. } => {
            assert!(
                diagnostics.iter().any(|diagnostic| diagnostic.code == expected),
                "expected diagnostic {expected:?}, got {diagnostics:#?}"
            );
        }
        other => panic!("expected validation error {expected}, got {other:?}"),
    }
}

#[test]
fn sample_fixture_passes_schema_and_semantic_validation() {
    let project = store()
        .parse_json(&serde_json::to_string(&sample_project()).unwrap())
        .unwrap();

    assert_eq!(project.name(), "LaunchForge Sample");
    assert_eq!(project.schema_version(), PROJECT_SCHEMA_VERSION);
    assert_eq!(
        project.project_id(),
        "11111111-1111-4111-8111-111111111111"
    );
}

#[test]
fn create_save_open_round_trip_preserves_project_and_entity_ids() {
    let store = store();
    let directory = tempdir().unwrap();
    let path = directory.path().join("my-launcher.lfproject");

    let created = store.create("My Launcher").unwrap();
    let original_id = created.project_id().to_owned();
    let original_root_id = created.as_value()["components"][0]["id"]
        .as_str()
        .unwrap()
        .to_owned();

    store.save(&path, &created).unwrap();
    let opened = store.open(&path).unwrap();

    assert_eq!(opened.as_value(), created.as_value());
    assert_eq!(opened.project_id(), original_id);
    assert_eq!(
        opened.as_value()["components"][0]["id"].as_str().unwrap(),
        original_root_id.as_str()
    );

    // Saving the same document again must not allocate new IDs.
    store.save(&path, &opened).unwrap();
    let reopened = store.open(&path).unwrap();
    assert_eq!(reopened.as_value(), opened.as_value());
}

#[test]
fn new_projects_receive_unique_uuid_v4_ids_and_a_valid_empty_root() {
    let store = store();
    let first = store.create("First").unwrap();
    let second = store.create("Second").unwrap();

    assert_ne!(first.project_id(), second.project_id());
    assert_eq!(Uuid::parse_str(first.project_id()).unwrap().get_version(), Some(uuid::Version::Random));
    assert_eq!(first.as_value()["assets"].as_array().unwrap().len(), 1);
    assert_eq!(first.as_value()["assets"][0]["kind"], "applicationIcon");
    assert_eq!(first.as_value()["assets"][0]["path"], "assets/launcher-icon.ico");
    assert_eq!(first.as_value()["window"]["iconAssetId"], first.as_value()["assets"][0]["id"]);
    assert_eq!(first.as_value()["games"], json!([]));
    assert_eq!(first.as_value()["components"][0]["type"], "container");
    assert_eq!(first.as_value()["components"][0]["children"], json!([]));
}

#[test]
fn create_rejects_blank_or_oversized_project_names() {
    let store = store();

    assert!(matches!(
        store.create("   "),
        Err(ProjectError::InvalidProjectName)
    ));
    assert!(matches!(
        store.create(&"x".repeat(81)),
        Err(ProjectError::InvalidProjectName)
    ));
}

#[test]
fn parser_rejects_malformed_json_and_invalid_utf8() {
    let store = store();

    assert!(matches!(
        store.parse_json("{ definitely not json"),
        Err(ProjectError::InvalidJson(_))
    ));
    assert!(matches!(
        store.validator().parse_bytes(&[0xff, 0xfe]),
        Err(ProjectError::InvalidUtf8)
    ));
}

#[test]
fn parser_rejects_projects_over_the_documented_size_limit() {
    let store = store();
    let bytes = vec![b' '; MAX_PROJECT_BYTES + 1];

    assert!(matches!(
        store.validator().parse_bytes(&bytes),
        Err(ProjectError::ProjectTooLarge { .. })
    ));
}

#[test]
fn schema_rejects_unknown_fields_and_reports_unsupported_versions() {
    let store = store();

    let mut unknown_field = sample_project();
    unknown_field["unexpected"] = json!(true);
    expect_validation_code(
        store.validator().validate(&unknown_field).unwrap_err(),
        "SCHEMA_VALIDATION_FAILED",
    );

    for unsupported_version in [json!(0), json!(2)] {
        let mut project = sample_project();
        project["schemaVersion"] = unsupported_version;
        expect_validation_code(
            store.validator().validate(&project).unwrap_err(),
            "UNSUPPORTED_SCHEMA_VERSION",
        );
    }
}

#[test]
fn schema_rejects_invalid_component_properties() {
    let store = store();
    let mut project = sample_project();
    project["components"][0]["props"]["gap"] = json!(-1);

    expect_validation_code(
        store.validator().validate(&project).unwrap_err(),
        "SCHEMA_VALIDATION_FAILED",
    );
}

#[test]
fn semantic_validation_rejects_duplicate_ids_across_entity_types() {
    let store = store();
    let mut project = sample_project();
    let asset_id = project["assets"][0]["id"].clone();
    project["games"][0]["id"] = asset_id;

    expect_validation_code(
        store.validator().validate(&project).unwrap_err(),
        "DUPLICATE_ID",
    );
}

#[test]
fn schema_rejects_noncanonical_uppercase_uuids() {
    let store = store();

    let mut entity_id = sample_project();
    entity_id["projectId"] = json!("ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF");
    expect_validation_code(
        store.validator().validate(&entity_id).unwrap_err(),
        "SCHEMA_VALIDATION_FAILED",
    );

    let mut reference_id = sample_project();
    reference_id["window"]["iconAssetId"] = json!("CCCCCCCC-CCCC-4CCC-8CCC-CCCCCCCCCCCC");
    expect_validation_code(
        store.validator().validate(&reference_id).unwrap_err(),
        "SCHEMA_VALIDATION_FAILED",
    );
}

#[test]
fn semantic_validation_requires_a_typed_application_icon_asset() {
    let store = store();

    let mut missing_icon = sample_project();
    missing_icon["window"]["iconAssetId"] = json!("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    expect_validation_code(
        store.validator().validate(&missing_icon).unwrap_err(),
        "MISSING_APP_ICON",
    );

    let mut wrong_kind = sample_project();
    wrong_kind["window"]["iconAssetId"] = wrong_kind["assets"][0]["id"].clone();
    expect_validation_code(
        store.validator().validate(&wrong_kind).unwrap_err(),
        "INVALID_APP_ICON",
    );

    let mut wrong_icon_extension = sample_project();
    wrong_icon_extension["assets"][1]["path"] = json!("assets/launcher-icon.png");
    expect_validation_code(
        store.validator().validate(&wrong_icon_extension).unwrap_err(),
        "SCHEMA_VALIDATION_FAILED",
    );

    let mut ico_as_image = sample_project();
    ico_as_image["assets"][0]["path"] = json!("assets/cover.ico");
    expect_validation_code(
        store.validator().validate(&ico_as_image).unwrap_err(),
        "SCHEMA_VALIDATION_FAILED",
    );

    // The schema now rejects .ico in image assets case-insensitively.
    let mut uppercase_ico_as_image = sample_project();
    uppercase_ico_as_image["assets"][0]["path"] = json!("assets/cover.ICO");
    expect_validation_code(
        store.validator().validate(&uppercase_ico_as_image).unwrap_err(),
        "SCHEMA_VALIDATION_FAILED",
    );
}

#[test]
fn semantic_validation_rejects_missing_asset_and_game_references() {
    let store = store();

    let mut missing_image_asset = sample_project();
    missing_image_asset["components"][0]["children"][1]["props"]["assetId"] =
        json!("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    expect_validation_code(
        store
            .validator()
            .validate(&missing_image_asset)
            .unwrap_err(),
        "MISSING_ASSET",
    );

    let mut missing_launch_game = sample_project();
    missing_launch_game["components"][0]["children"][5]["props"]["action"]["gameId"] =
        json!("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    expect_validation_code(
        store
            .validator()
            .validate(&missing_launch_game)
            .unwrap_err(),
        "MISSING_GAME",
    );
}

#[test]
fn semantic_validation_rejects_windows_reserved_and_nonportable_asset_paths() {
    let store = store();

    for path in ["assets/CON.txt", "assets/NUL"] {
        let mut project = sample_project();
        project["assets"][0]["path"] = json!(path);

        expect_validation_code(
            store.validator().validate(&project).unwrap_err(),
            "UNSAFE_ASSET_PATH",
        );
    }

    let mut trailing_dot = sample_project();
    trailing_dot["assets"][0]["path"] = json!("assets/file.");
    expect_validation_code(
        store.validator().validate(&trailing_dot).unwrap_err(),
        "SCHEMA_VALIDATION_FAILED",
    );
}

#[test]
fn semantic_validation_rejects_case_insensitive_asset_path_collisions() {
    let store = store();
    let mut project = sample_project();
    let mut second_asset = project["assets"][0].clone();
    second_asset["id"] = json!("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    second_asset["path"] = json!("assets/SAMPLE-COVER.svg");
    project["assets"].as_array_mut().unwrap().push(second_asset);

    expect_validation_code(
        store.validator().validate(&project).unwrap_err(),
        "DUPLICATE_ASSET_PATH",
    );
}

#[test]
fn semantic_validation_rejects_inconsistent_window_minimums() {
    let store = store();
    let mut min_width = sample_project();
    min_width["window"]["minWidth"] = json!(1200);
    expect_validation_code(
        store.validator().validate(&min_width).unwrap_err(),
        "INVALID_WINDOW",
    );

    let mut min_height = sample_project();
    min_height["window"]["minHeight"] = json!(900);
    expect_validation_code(
        store.validator().validate(&min_height).unwrap_err(),
        "INVALID_WINDOW",
    );
}

#[test]
fn schema_requires_one_root_container() {
    let store = store();
    let mut project = sample_project();
    project["components"][0]["type"] = json!("text");
    project["components"][0]["props"] = json!({
        "value": "Not a root container",
        "fontSize": 20,
        "color": "text"
    });
    project["components"][0].as_object_mut().unwrap().remove("children");

    expect_validation_code(
        store.validator().validate(&project).unwrap_err(),
        "SCHEMA_VALIDATION_FAILED",
    );
}

#[test]
fn save_revalidates_documents_after_mutation() {
    let store = store();
    let directory = tempdir().unwrap();
    let path = directory.path().join("invalid.lfproject");
    let mut project = store.create("Editable").unwrap();

    project.as_value_mut()["name"] = json!("");
    expect_validation_code(
        store.save(&path, &project).unwrap_err(),
        "SCHEMA_VALIDATION_FAILED",
    );
    assert!(!path.exists());
}

#[test]
fn save_replaces_an_existing_project_without_partial_json() {
    let store = store();
    let directory = tempdir().unwrap();
    let path = directory.path().join("project.lfproject");
    let first = store.create("First version").unwrap();
    let second = store.create("Second version").unwrap();

    store.save(&path, &first).unwrap();
    store.save(&path, &second).unwrap();

    let opened = store.open(&path).unwrap();
    assert_eq!(opened.as_value(), second.as_value());
    assert_eq!(
        serde_json::from_slice::<Value>(&fs::read(&path).unwrap()).unwrap(),
        *second.as_value()
    );
}


#[test]
fn semantic_validation_rejects_whitespace_only_user_facing_strings() {
    let store = store();

    let mut project_name = sample_project();
    project_name["name"] = json!("   ");
    expect_validation_code(
        store.validator().validate(&project_name).unwrap_err(),
        "INVALID_STRING",
    );

    let mut window_title = sample_project();
    window_title["window"]["title"] = json!("   ");
    expect_validation_code(
        store.validator().validate(&window_title).unwrap_err(),
        "INVALID_STRING",
    );

    let mut game_title = sample_project();
    game_title["games"][0]["title"] = json!("   ");
    expect_validation_code(
        store.validator().validate(&game_title).unwrap_err(),
        "INVALID_STRING",
    );

    let mut button_label = sample_project();
    button_label["components"][0]["children"][4]["props"]["label"] = json!("   ");
    expect_validation_code(
        store.validator().validate(&button_label).unwrap_err(),
        "INVALID_STRING",
    );
}

#[test]
fn semantic_validation_rejects_component_depth_over_the_v1_limit() {
    let store = store();
    let mut project = sample_project();

    let mut node = json!({
        "id": Uuid::new_v4().to_string(),
        "type": "text",
        "props": {
            "value": "deep leaf",
            "fontSize": 20,
            "color": "text"
        }
    });

    // One leaf plus MAX_COMPONENT_DEPTH container levels creates depth 17.
    for _ in 0..16 {
        node = json!({
            "id": Uuid::new_v4().to_string(),
            "type": "container",
            "props": {
                "axis": "vertical",
                "gap": 0,
                "padding": 0,
                "background": "surface"
            },
            "children": [node]
        });
    }
    project["components"][0] = node;

    expect_validation_code(
        store.validator().validate(&project).unwrap_err(),
        "COMPONENT_DEPTH_LIMIT",
    );
}

#[test]
fn semantic_validation_rejects_component_count_over_the_v1_limit() {
    let store = store();
    let mut project = sample_project();
    let mut containers = Vec::new();

    for _ in 0..4 {
        let children: Vec<Value> = (0..32)
            .map(|_| {
                json!({
                    "id": Uuid::new_v4().to_string(),
                    "type": "text",
                    "props": {
                        "value": "fixture",
                        "fontSize": 12,
                        "color": "text"
                    }
                })
            })
            .collect();

        containers.push(json!({
            "id": Uuid::new_v4().to_string(),
            "type": "container",
            "props": {
                "axis": "vertical",
                "gap": 0,
                "padding": 0,
                "background": "surface"
            },
            "children": children
        }));
    }

    project["components"][0]["children"] = json!(containers);
    expect_validation_code(
        store.validator().validate(&project).unwrap_err(),
        "COMPONENT_LIMIT",
    );
}

#[test]
fn schema_diagnostics_do_not_echo_invalid_field_values() {
    let store = store();
    let secret_canary = "synthetic-secret-canary-do-not-log";
    let mut project = sample_project();
    project["theme"]["surface"] = json!(secret_canary);

    match store.validator().validate(&project).unwrap_err() {
        ProjectError::ValidationFailed { diagnostics, .. } => {
            assert!(!diagnostics.is_empty());
            assert!(diagnostics.iter().all(|diagnostic| {
                !diagnostic.message.contains(secret_canary)
            }));
            assert!(diagnostics.iter().any(|diagnostic| {
                diagnostic.path == "/theme/surface"
            }));
        }
        other => panic!("expected schema validation failure, got {other:?}"),
    }
}

#[test]
fn file_errors_do_not_echo_private_local_paths() {
    let store = store();
    let directory = tempdir().unwrap();
    let private_path = directory.path().join("private-workspace-project.lfproject");
    let private_path_text = private_path.to_string_lossy().to_string();

    let error = store.open(&private_path).unwrap_err();
    assert!(!error.to_string().contains(&private_path_text));
}

#[cfg(unix)]
#[test]
fn open_and_save_reject_symbolic_link_project_paths() {
    use std::os::unix::fs::symlink;

    let store = store();
    let directory = tempdir().unwrap();
    let real_path = directory.path().join("real.lfproject");
    let link_path = directory.path().join("linked.lfproject");
    let project = store.create("Protected target").unwrap();

    store.save(&real_path, &project).unwrap();
    symlink(&real_path, &link_path).unwrap();

    assert!(matches!(
        store.open(&link_path),
        Err(ProjectError::SymbolicLinkProject)
    ));
    assert!(matches!(
        store.save(&link_path, &project),
        Err(ProjectError::SymbolicLinkProject)
    ));
}
