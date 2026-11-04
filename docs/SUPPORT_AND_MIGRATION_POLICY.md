# Support boundaries and migration policy

**Status:** Policy proposal for the Windows-first MVP. It does not announce a supported OS/package version because the Phase 0/1 baseline is not approved yet.

## Support boundaries

LaunchForge support must be limited to release combinations that have passed clean-machine tests and appear in a published support matrix. A successful developer-machine build, a Python reference prototype, or an unreviewed PR is not a supported product release.

The future support matrix must identify separately:

- Studio version and supported Windows baseline.
- Launcher Runtime version and supported Windows baseline.
- Package/install format and architecture.
- Project schema version and migration compatibility.
- Launcher updater/bootstrapper version and accepted trust metadata generation.
- Game-delivery subsystem version, if enabled.

Studio, exported Launcher, game operations and launcher self-update are separate support surfaces. Support for one does not imply support for the others.

Until there is an approved baseline:
- no Windows minimum/maximum versions should be advertised;
- no installer/portable package type should be promised;
- no automatic self-update should be enabled;
- no production SLA, telemetry availability or hosted diagnostic endpoint should be implied.

Support excludes publisher-managed APIs/CDNs, game files and signing services unless explicitly covered by a separate agreement. LaunchForge cannot recover a publisher's lost private signing keys or vouch for a publisher's own backend availability.

## Project and runtime migration

1. Record the source project schema, Runtime and package versions before migration.
2. Validate and create a recoverable backup before modifying any project or installed runtime state.
3. Run explicit, versioned migration steps; do not infer a migration from a newer application version alone.
4. Preserve unknown/unsupported fields semantically unless an approved migration explicitly changes or removes them. Never silently discard unknown project data.
5. Make migrations deterministic and idempotent where practical. Record the migration ID and source/target schema versions without storing project contents in logs.
6. Provide a dry-run/diagnostic result before destructive changes.
7. On migration failure, leave the original project or prior Runtime slot untouched and explain the recovery action through a stable error code.
8. Do not open-and-resave a project in a way that silently rewrites data merely because it was viewed.
9. Keep game content migration/update state distinct from launcher application/schema migration state.

## Backward compatibility and deprecation

A release must publish its supported schema/Runtime compatibility range and deprecation window. A project outside that range must receive an explicit unsupported/migration diagnostic; it must not be silently “best-effort” rewritten.

For each schema or Runtime migration publish: source versions, target version, transformation summary, fields affected, backup/rollback procedure, compatibility impact, and a fixture demonstrating semantic preservation. Remove a compatibility path only through a reviewed release note and an explicit minimum-version change.

## Support bundle handling

Support bundles follow [DIAGNOSTICS_AND_CRASH_REPORTING.md](DIAGNOSTICS_AND_CRASH_REPORTING.md). Do not request raw logs, project files, game manifests, environment dumps or process memory as a default troubleshooting step. Ask only for the sanitized fields needed for the specific error. A user must choose whether to share a support bundle.
