//! Project foundation for LaunchForge Phase 1.1.
//!
//! This crate consumes the candidate schema stored at
//! poc/contracts/project-v1.schema.json without copying or redefining it.
//! The schema is compiled once per ProjectStore; semantic checks below
//! enforce cross-entity references and constraints that JSON Schema alone
//! cannot express.

use std::collections::HashSet;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use jsonschema::Validator;
use serde_json::{Value, json};
use thiserror::Error;
use uuid::Uuid;

pub const PROJECT_FORMAT: &str = "launchforge.project";
pub const PROJECT_SCHEMA_VERSION: u64 = 1;
pub const MAX_PROJECT_BYTES: usize = 1024 * 1024;
pub const MAX_COMPONENTS: usize = 128;
pub const MAX_COMPONENT_DEPTH: usize = 16;

const PROJECT_SCHEMA_V1: &str =
    include_str!("../../../poc/contracts/project-v1.schema.json");

/// A stable, user-actionable validation diagnostic.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationDiagnostic {
    pub code: String,
    pub path: String,
    pub message: String,
}

impl ValidationDiagnostic {
    fn new(
        code: impl Into<String>,
        path: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            code: code.into(),
            path: path.into(),
            message: message.into(),
        }
    }
}

/// Errors returned by project parsing, validation, persistence, and creation.
#[derive(Debug, Error)]
pub enum ProjectError {
    #[error("project input is not valid UTF-8")]
    InvalidUtf8,

    #[error("project JSON is invalid: {0}")]
    InvalidJson(#[from] serde_json::Error),

    #[error("project is {actual_bytes} bytes; the limit is {max_bytes} bytes")]
    ProjectTooLarge {
        actual_bytes: usize,
        max_bytes: usize,
    },

    #[error("project schema could not be loaded or compiled: {0}")]
    SchemaCompile(String),

    #[error("project failed validation with {diagnostics_count} diagnostic(s)")]
    ValidationFailed {
        diagnostics: Vec<ValidationDiagnostic>,
        diagnostics_count: usize,
    },

    #[error("project name must contain 1 to 80 non-whitespace characters")]
    InvalidProjectName,

    #[error("project path has no filename: {0}")]
    InvalidProjectPath(PathBuf),

    #[error("refusing to open or replace a symbolic-link project file: {0}")]
    SymbolicLinkProject(PathBuf),

    #[error("I/O error for {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
}

fn io_error(path: &Path, source: std::io::Error) -> ProjectError {
    ProjectError::Io {
        path: path.to_path_buf(),
        source,
    }
}

/// A parsed project document.
///
/// The inner JSON value is intentionally exposed read-only by default. Editor
/// code may obtain a mutable reference, but ProjectStore::save always
/// re-validates the complete document before writing it.
#[derive(Debug, Clone, PartialEq)]
pub struct ProjectDocument {
    value: Value,
}

impl ProjectDocument {
    pub fn as_value(&self) -> &Value {
        &self.value
    }

    /// Mutable access for a future editor command layer.
    ///
    /// Mutations are not trusted: saving always validates the resulting value.
    pub fn as_value_mut(&mut self) -> &mut Value {
        &mut self.value
    }

    pub fn project_id(&self) -> &str {
        self.value
            .get("projectId")
            .and_then(Value::as_str)
            .expect("validated project always has a projectId")
    }

    pub fn name(&self) -> &str {
        self.value
            .get("name")
            .and_then(Value::as_str)
            .expect("validated project always has a name")
    }

    pub fn schema_version(&self) -> u64 {
        self.value
            .get("schemaVersion")
            .and_then(Value::as_u64)
            .expect("validated project always has a schemaVersion")
    }

    /// Serialize semantically unchanged project data as formatted UTF-8 JSON.
    pub fn to_json_pretty(&self) -> Result<Vec<u8>, ProjectError> {
        let mut bytes = serde_json::to_vec_pretty(&self.value)?;
        bytes.push(b'\n');
        Ok(bytes)
    }
}

/// The compiled project v1 validator.
///
/// The normative JSON Schema remains in the single repository-owned schema
/// file. This type adds only semantic checks that need to inspect relationships
/// between different entities in the same project.
#[derive(Debug)]
pub struct ProjectValidator {
    schema_validator: Validator,
}

impl ProjectValidator {
    pub fn embedded_v1() -> Result<Self, ProjectError> {
        Self::from_schema_json(PROJECT_SCHEMA_V1)
    }

    /// Build a validator from an explicitly supplied schema document.
    ///
    /// Production callers should normally use embedded_v1, which compiles
    /// the single repository-owned schema file.
    pub fn from_schema_json(schema_json: &str) -> Result<Self, ProjectError> {
        let schema: Value = serde_json::from_str(schema_json)
            .map_err(|error| ProjectError::SchemaCompile(error.to_string()))?;

        let schema_validator = jsonschema::validator_for(&schema)
            .map_err(|error| ProjectError::SchemaCompile(error.to_string()))?;

        Ok(Self { schema_validator })
    }

    pub fn validate(&self, project: &Value) -> Result<(), ProjectError> {
        let mut diagnostics = Vec::new();

        for error in self.schema_validator.iter_errors(project) {
            diagnostics.push(ValidationDiagnostic::new(
                "SCHEMA_VALIDATION_FAILED",
                error.instance_path().to_string(),
                error.to_string(),
            ));
        }

        if !diagnostics.is_empty() {
            return Err(validation_error(diagnostics));
        }

        validate_semantics(project)
    }

    pub fn parse_json(&self, json_text: &str) -> Result<ProjectDocument, ProjectError> {
        let input_bytes = json_text.as_bytes().len();
        if input_bytes > MAX_PROJECT_BYTES {
            return Err(ProjectError::ProjectTooLarge {
                actual_bytes: input_bytes,
                max_bytes: MAX_PROJECT_BYTES,
            });
        }

        let value: Value = serde_json::from_str(json_text)?;
        self.validate(&value)?;
        Ok(ProjectDocument { value })
    }

    pub fn parse_bytes(&self, bytes: &[u8]) -> Result<ProjectDocument, ProjectError> {
        if bytes.len() > MAX_PROJECT_BYTES {
            return Err(ProjectError::ProjectTooLarge {
                actual_bytes: bytes.len(),
                max_bytes: MAX_PROJECT_BYTES,
            });
        }

        let text = std::str::from_utf8(bytes).map_err(|_| ProjectError::InvalidUtf8)?;
        self.parse_json(text)
    }
}

/// The P1-A project create/open/save service.
#[derive(Debug)]
pub struct ProjectStore {
    validator: ProjectValidator,
}

impl ProjectStore {
    /// Construct a store using the repository's single project-v1 schema.
    pub fn new() -> Result<Self, ProjectError> {
        Ok(Self {
            validator: ProjectValidator::embedded_v1()?,
        })
    }

    /// Construct a store with a schema supplied by an integration harness.
    ///
    /// This is useful for contract tests. Application code should use new
    /// unless a reviewed contract migration explicitly requires otherwise.
    pub fn with_schema_json(schema_json: &str) -> Result<Self, ProjectError> {
        Ok(Self {
            validator: ProjectValidator::from_schema_json(schema_json)?,
        })
    }

    pub fn validator(&self) -> &ProjectValidator {
        &self.validator
    }

    /// Create a valid empty project using the v1 starter defaults.
    ///
    /// IDs are generated once and stored in the document. Save/open does not
    /// regenerate them.
    pub fn create(&self, name: &str) -> Result<ProjectDocument, ProjectError> {
        if name.trim().is_empty() || name.chars().count() > 80 {
            return Err(ProjectError::InvalidProjectName);
        }

        let project_id = Uuid::new_v4().to_string();
        let root_id = Uuid::new_v4().to_string();

        let value = json!({
            "format": PROJECT_FORMAT,
            "schemaVersion": PROJECT_SCHEMA_VERSION,
            "projectId": project_id,
            "name": name,
            "window": {
                "title": name,
                "width": 960,
                "height": 640,
                "minWidth": 640,
                "minHeight": 480,
                "resizable": true
            },
            "theme": {
                "surface": "#121826",
                "text": "#f5f7fa",
                "accent": "#6aa9ff"
            },
            "assets": [],
            "games": [],
            "components": [{
                "id": root_id,
                "type": "container",
                "props": {
                    "axis": "vertical",
                    "gap": 16,
                    "padding": 24,
                    "background": "surface"
                },
                "children": []
            }]
        });

        self.validator.validate(&value)?;
        Ok(ProjectDocument { value })
    }

    /// Open, size-check, parse, and validate a project file.
    ///
    /// This method does not resolve or read asset paths. Asset access must be
    /// performed later by the privileged host after canonical containment and
    /// reparse-point checks.
    pub fn open(&self, path: impl AsRef<Path>) -> Result<ProjectDocument, ProjectError> {
        let path = path.as_ref();

        let metadata = fs::symlink_metadata(path).map_err(|error| io_error(path, error))?;
        if metadata.file_type().is_symlink() {
            return Err(ProjectError::SymbolicLinkProject(path.to_path_buf()));
        }
        if metadata.len() > MAX_PROJECT_BYTES as u64 {
            return Err(ProjectError::ProjectTooLarge {
                actual_bytes: usize::try_from(metadata.len()).unwrap_or(usize::MAX),
                max_bytes: MAX_PROJECT_BYTES,
            });
        }

        let mut file = File::open(path).map_err(|error| io_error(path, error))?;
        let mut bytes = Vec::with_capacity(metadata.len() as usize);
        file.take((MAX_PROJECT_BYTES + 1) as u64)
            .read_to_end(&mut bytes)
            .map_err(|error| io_error(path, error))?;

        self.validator.parse_bytes(&bytes)
    }

    /// Validate and atomically replace a project file.
    ///
    /// The temporary file is created in the destination directory, flushed,
    /// and then renamed over the selected destination. This avoids exposing a
    /// partially written JSON document if the process is interrupted.
    pub fn save(
        &self,
        path: impl AsRef<Path>,
        document: &ProjectDocument,
    ) -> Result<(), ProjectError> {
        let path = path.as_ref();
        self.validator.validate(document.as_value())?;
        let bytes = document.to_json_pretty()?;
        atomic_replace(path, &bytes)
    }

    /// Parse and validate an in-memory project without touching the filesystem.
    pub fn parse_json(&self, json_text: &str) -> Result<ProjectDocument, ProjectError> {
        self.validator.parse_json(json_text)
    }
}

fn validation_error(diagnostics: Vec<ValidationDiagnostic>) -> ProjectError {
    let diagnostics_count = diagnostics.len();
    ProjectError::ValidationFailed {
        diagnostics,
        diagnostics_count,
    }
}

fn semantic_failure(
    code: &str,
    path: impl Into<String>,
    message: impl Into<String>,
) -> ProjectError {
    validation_error(vec![ValidationDiagnostic::new(code, path, message)])
}

fn string_at<'a>(value: &'a Value, key: &str) -> Option<&'a str> {
    value.get(key).and_then(Value::as_str)
}

fn normalized_id(value: &str) -> String {
    value.to_ascii_lowercase()
}

fn insert_unique_id(
    ids: &mut HashSet<String>,
    id: &str,
    path: &str,
) -> Result<(), ProjectError> {
    if !ids.insert(normalized_id(id)) {
        return Err(semantic_failure(
            "DUPLICATE_ID",
            path,
            "Entity IDs must be unique across the project, assets, games, and components",
        ));
    }
    Ok(())
}

fn validate_portable_asset_path(path: &str, diagnostic_path: &str) -> Result<(), ProjectError> {
    let Some(filename) = path.strip_prefix("assets/") else {
        return Err(semantic_failure(
            "UNSAFE_ASSET_PATH",
            diagnostic_path,
            "Asset paths must be relative and start with assets/",
        ));
    };

    if filename.is_empty()
        || filename.contains('/')
        || filename.contains('\\')
        || filename.contains(':')
        || filename.contains('%')
        || filename.contains('?')
        || filename.ends_with('.')
        || filename.ends_with(' ')
        || !filename
            .as_bytes()
            .first()
            .is_some_and(u8::is_ascii_alphanumeric)
        || filename.len() > 120
        || !filename
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"._-".contains(&byte))
    {
        return Err(semantic_failure(
            "UNSAFE_ASSET_PATH",
            diagnostic_path,
            "Asset path must contain one portable filename under assets/",
        ));
    }

    let basename = filename.split('.').next().unwrap_or(filename);
    let lower = basename.to_ascii_lowercase();
    let reserved = matches!(lower.as_str(), "con" | "prn" | "aux" | "nul")
        || (lower.len() == 4
            && (lower.starts_with("com") || lower.starts_with("lpt"))
            && lower.as_bytes()[3].is_ascii_digit()
            && lower.as_bytes()[3] != b'0');

    if reserved {
        return Err(semantic_failure(
            "UNSAFE_ASSET_PATH",
            diagnostic_path,
            "Asset path uses a reserved Windows device name",
        ));
    }

    Ok(())
}

fn validate_semantics(project: &Value) -> Result<(), ProjectError> {
    let mut ids = HashSet::new();
    let project_id = string_at(project, "projectId").expect("schema requires projectId");
    insert_unique_id(&mut ids, project_id, "$.projectId")?;

    let window = project.get("window").expect("schema requires window");
    let width = window["width"].as_u64().expect("schema validates width");
    let height = window["height"].as_u64().expect("schema validates height");
    let min_width = window["minWidth"]
        .as_u64()
        .expect("schema validates minWidth");
    let min_height = window["minHeight"]
        .as_u64()
        .expect("schema validates minHeight");

    if min_width > width {
        return Err(semantic_failure(
            "INVALID_WINDOW",
            "$.window.minWidth",
            "Minimum window width cannot exceed the default width",
        ));
    }
    if min_height > height {
        return Err(semantic_failure(
            "INVALID_WINDOW",
            "$.window.minHeight",
            "Minimum window height cannot exceed the default height",
        ));
    }

    let assets = project["assets"].as_array().expect("schema validates assets");
    let mut asset_ids = HashSet::new();
    let mut asset_paths = HashSet::new();

    for (index, asset) in assets.iter().enumerate() {
        let path = format!("$.assets[{index}]");
        let id = string_at(asset, "id").expect("schema validates asset id");
        insert_unique_id(&mut ids, id, &format!("{path}.id"))?;
        asset_ids.insert(normalized_id(id));

        let asset_path = string_at(asset, "path").expect("schema validates asset path");
        validate_portable_asset_path(asset_path, &format!("{path}.path"))?;
        if !asset_paths.insert(asset_path.to_ascii_lowercase()) {
            return Err(semantic_failure(
                "DUPLICATE_ASSET_PATH",
                format!("{path}.path"),
                "Asset paths must be unique without regard to case",
            ));
        }
    }

    let games = project["games"].as_array().expect("schema validates games");
    let mut game_ids = HashSet::new();
    for (index, game) in games.iter().enumerate() {
        let path = format!("$.games[{index}]");
        let id = string_at(game, "id").expect("schema validates game id");
        insert_unique_id(&mut ids, id, &format!("{path}.id"))?;
        game_ids.insert(normalized_id(id));

        let cover_id = string_at(game, "coverAssetId").expect("schema validates coverAssetId");
        if !asset_ids.contains(&normalized_id(cover_id)) {
            return Err(semantic_failure(
                "MISSING_ASSET",
                format!("{path}.coverAssetId"),
                "Game cover references an unknown asset",
            ));
        }
    }

    let components = project["components"]
        .as_array()
        .expect("schema validates components");

    // The v1 contract calls for exactly one root container. The JSON Schema's
    // oneOf validates node shapes, while this check enforces root semantics.
    if string_at(&components[0], "type") != Some("container") {
        return Err(semantic_failure(
            "INVALID_ROOT_COMPONENT",
            "$.components[0].type",
            "Schema v1 requires the single root component to be a container",
        ));
    }

    let mut component_count = 0usize;
    for (index, component) in components.iter().enumerate() {
        validate_component(
            component,
            1,
            &format!("$.components[{index}]"),
            &mut ids,
            &asset_ids,
            &game_ids,
            &mut component_count,
        )?;
    }

    Ok(())
}

fn validate_component(
    component: &Value,
    depth: usize,
    path: &str,
    ids: &mut HashSet<String>,
    asset_ids: &HashSet<String>,
    game_ids: &HashSet<String>,
    component_count: &mut usize,
) -> Result<(), ProjectError> {
    *component_count += 1;
    if *component_count > MAX_COMPONENTS {
        return Err(semantic_failure(
            "COMPONENT_LIMIT",
            path,
            format!("At most {MAX_COMPONENTS} components are allowed"),
        ));
    }
    if depth > MAX_COMPONENT_DEPTH {
        return Err(semantic_failure(
            "COMPONENT_DEPTH_LIMIT",
            path,
            format!("Component nesting exceeds {MAX_COMPONENT_DEPTH}"),
        ));
    }

    let id = string_at(component, "id").expect("schema validates component id");
    insert_unique_id(ids, id, &format!("{path}.id"))?;

    let component_type = string_at(component, "type").expect("schema validates component type");
    let props = component.get("props").expect("schema validates props");

    match component_type {
        "container" => {
            let children = component["children"]
                .as_array()
                .expect("schema validates container children");
            for (index, child) in children.iter().enumerate() {
                validate_component(
                    child,
                    depth + 1,
                    &format!("{path}.children[{index}]"),
                    ids,
                    asset_ids,
                    game_ids,
                    component_count,
                )?;
            }
        }
        "image" => {
            let asset_id = string_at(props, "assetId").expect("schema validates assetId");
            if !asset_ids.contains(&normalized_id(asset_id)) {
                return Err(semantic_failure(
                    "MISSING_ASSET",
                    format!("{path}.props.assetId"),
                    "Image references an unknown asset",
                ));
            }
        }
        "text" => {
            if let Some(binding) = props.get("value").filter(|value| value.is_object()) {
                let game_id =
                    string_at(binding, "gameId").expect("schema validates binding gameId");
                if !game_ids.contains(&normalized_id(game_id)) {
                    return Err(semantic_failure(
                        "MISSING_GAME",
                        format!("{path}.props.value.gameId"),
                        "Text binding references an unknown game",
                    ));
                }
            }
        }
        "button" => {
            let action = props.get("action").expect("schema validates action");
            if string_at(action, "type") == Some("launchGame") {
                let game_id =
                    string_at(action, "gameId").expect("schema validates launchGame gameId");
                if !game_ids.contains(&normalized_id(game_id)) {
                    return Err(semantic_failure(
                        "MISSING_GAME",
                        format!("{path}.props.action.gameId"),
                        "Launch action references an unknown game",
                    ));
                }
            }
        }
        "gameCard" => {
            let game_id = string_at(props, "gameId").expect("schema validates gameId");
            if !game_ids.contains(&normalized_id(game_id)) {
                return Err(semantic_failure(
                    "MISSING_GAME",
                    format!("{path}.props.gameId"),
                    "Game card references an unknown game",
                ));
            }
        }
        _ => unreachable!("schema rejects unsupported component types"),
    }

    Ok(())
}

struct TemporaryFile {
    path: PathBuf,
    committed: bool,
}

impl Drop for TemporaryFile {
    fn drop(&mut self) {
        if !self.committed {
            let _ = fs::remove_file(&self.path);
        }
    }
}

fn atomic_replace(path: &Path, bytes: &[u8]) -> Result<(), ProjectError> {
    let file_name = path
        .file_name()
        .ok_or_else(|| ProjectError::InvalidProjectPath(path.to_path_buf()))?;

    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));

    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err(ProjectError::SymbolicLinkProject(path.to_path_buf()));
        }
        Ok(metadata) if !metadata.is_file() => {
            return Err(io_error(
                path,
                std::io::Error::new(
                    std::io::ErrorKind::InvalidInput,
                    "project destination is not a regular file",
                ),
            ));
        }
        Ok(_) => {}
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(error) => return Err(io_error(path, error)),
    }

    let mut temporary_path = None;
    let mut temporary_file = None;

    for _ in 0..8 {
        let candidate = parent.join(format!(
            ".{}.{}.tmp",
            file_name.to_string_lossy(),
            Uuid::new_v4()
        ));

        match OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&candidate)
        {
            Ok(file) => {
                temporary_path = Some(candidate);
                temporary_file = Some(file);
                break;
            }
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(io_error(&candidate, error)),
        }
    }

    let temporary_path = temporary_path.ok_or_else(|| {
        io_error(
            parent,
            std::io::Error::new(
                std::io::ErrorKind::AlreadyExists,
                "could not allocate a unique temporary project file",
            ),
        )
    })?;
    let mut guard = TemporaryFile {
        path: temporary_path.clone(),
        committed: false,
    };

    let mut file = temporary_file.expect("temporary path and file are set together");
    file.write_all(bytes)
        .map_err(|error| io_error(&temporary_path, error))?;
    file.sync_all()
        .map_err(|error| io_error(&temporary_path, error))?;
    drop(file);

    replace_file(&temporary_path, path).map_err(|error| io_error(path, error))?;
    guard.committed = true;

    #[cfg(unix)]
    File::open(parent)
        .and_then(|directory| directory.sync_all())
        .map_err(|error| io_error(parent, error))?;

    Ok(())
}

#[cfg(windows)]
fn replace_file(source: &Path, destination: &Path) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Storage::FileSystem::{
        MOVEFILE_REPLACE_EXISTING, MOVEFILE_WRITE_THROUGH, MoveFileExW,
    };

    let source_wide: Vec<u16> = source.as_os_str().encode_wide().chain(Some(0)).collect();
    let destination_wide: Vec<u16> = destination
        .as_os_str()
        .encode_wide()
        .chain(Some(0))
        .collect();

    let result = unsafe {
        MoveFileExW(
            source_wide.as_ptr(),
            destination_wide.as_ptr(),
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH,
        )
    };

    if result == 0 {
        Err(std::io::Error::last_os_error())
    } else {
        Ok(())
    }
}

#[cfg(not(windows))]
fn replace_file(source: &Path, destination: &Path) -> std::io::Result<()> {
    fs::rename(source, destination)
}
