use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;

// Embedded at compile time — no filesystem lookup needed at runtime.
const DEFAULT_CONFIG: &str = include_str!("../../backend/config/config.json");

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SerialConfig {
    #[serde(rename = "Port")]
    pub port: String,

    #[serde(rename = "Baudrate")]
    pub baudrate: u32,

    #[serde(rename = "Bytesize")]
    pub bytesize: u8,

    #[serde(rename = "Parity")]
    pub parity: String,

    #[serde(rename = "Stopbits")]
    pub stopbits: f64,

    #[serde(rename = "Timeout")]
    pub timeout: f64,

    #[serde(rename = "Xonxoff")]
    pub xonxoff: bool,

    #[serde(rename = "Rtscts")]
    pub rtscts: bool,

    #[serde(rename = "Dsrdtr")]
    pub dsrdtr: bool,

    #[serde(rename = "WriteTimeout")]
    pub write_timeout: f64,
}



#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PumpConfig {

    #[serde(flatten)]
    pub serial: SerialConfig,

    #[serde(rename = "Pump Number")]
    pub pump_number: u32,

    #[serde(rename = "Flow Rate")]
    pub flow_rate: f64,
}



#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SelectorValveConfig {

    #[serde(flatten)]
    pub serial: SerialConfig,

    #[serde(rename = "Positions")]
    pub positions: u32,

    #[serde(rename = "Connections")]
    pub connections: HashMap<String, u32>,
}


#[derive(Debug, Serialize)]
pub struct ImportResult {
    added: Vec<String>,
    skipped: Vec<String>,
    pumps: Value,
}


fn config_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let dir = app
        .path()
        .app_config_dir()
        .map_err(|e| format!("Failed to resolve app config dir: {e}"))?;

    if !dir.exists() {
        fs::create_dir_all(&dir)
            .map_err(|e| format!("Failed to create app config dir: {e}"))?;
    }

    Ok(dir.join("config.json"))
}


fn ensure_config_exists(app: &tauri::AppHandle) -> Result<(), String> {
    let target = config_path(app)?;

    if target.exists() {
        return Ok(());
    }

    serde_json::from_str::<Value>(DEFAULT_CONFIG)
        .map_err(|e| format!("Embedded default config.json is invalid JSON: {e}"))?;

    fs::write(&target, DEFAULT_CONFIG)
        .map_err(|e| format!("Failed to seed config.json at {:?}: {e}", target))?;

    Ok(())
}


fn read_config(app: &tauri::AppHandle) -> Result<Value, String> {
    let path = config_path(app)?;

    let data = fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read config at {:?}: {e}", path))?;

    serde_json::from_str(&data)
        .map_err(|e| format!("Failed to parse config: {e}"))
}


fn write_config(app: &tauri::AppHandle, config: &Value) -> Result<(), String> {
    let path = config_path(app)?;

    let pretty = serde_json::to_string_pretty(config)
        .map_err(|e| format!("Failed to serialize config: {e}"))?;

    fs::write(&path, pretty)
        .map_err(|e| format!("Failed to write config at {:?}: {e}", path))
}


// Generic mutable device accessor
fn devices_object<'a>(
    config: &'a mut Value,
    device_type: &str,
) -> Result<&'a mut serde_json::Map<String, Value>, String> {

    config
        .get_mut("Devices")
        .and_then(|d| d.get_mut(device_type))
        .and_then(|v| v.as_object_mut())
        .ok_or_else(|| format!("{device_type} section not found in config"))
}


// Generic read-only device accessor
fn get_device_configs(
    config: &Value,
    device_type: &str,
) -> Result<Value, String> {

    config
        .get("Devices")
        .and_then(|d| d.get(device_type))
        .cloned()
        .ok_or_else(|| format!("{device_type} section not found in config"))
}


// Generic existence check
fn device_exists(
    config: &Value,
    device_type: &str,
    name: &str,
) -> Result<bool, String> {

    let devices = config
        .get("Devices")
        .and_then(|d| d.get(device_type))
        .and_then(|v| v.as_object())
        .ok_or_else(|| format!("{device_type} section not found in config"))?;

    Ok(devices.contains_key(name))
}


// -------------------------
// Config Getters
// -------------------------

#[tauri::command]
fn get_pump_configs(app: tauri::AppHandle) -> Result<Value, String> {
    let config = read_config(&app)?;
    get_device_configs(&config, "Pumps")
}


#[tauri::command]
fn get_valve_configs(app: tauri::AppHandle) -> Result<Value, String> {
    let config = read_config(&app)?;
    get_device_configs(&config, "Selector Valves")
}


#[tauri::command]
fn get_daq_configs(app: tauri::AppHandle) -> Result<Value, String> {
    let config = read_config(&app)?;
    get_device_configs(&config, "DAQs")
}


/// Return the "VD Routine" section of the config so the frontend can seed the
/// V/D measurement form with the saved sensor + routine defaults.
#[tauri::command]
fn get_vd_config(app: tauri::AppHandle) -> Result<Value, String> {
    let config = read_config(&app)?;
    config
        .get("VD Routine")
        .cloned()
        .ok_or_else(|| "VD Routine section not found in config".to_string())
}


// -------------------------
// Pump Operations
// -------------------------

#[tauri::command]
fn pump_config_exists(
    app: tauri::AppHandle,
    name: String,
) -> Result<bool, String> {

    let config = read_config(&app)?;
    device_exists(&config, "Pumps", &name)
}

#[tauri::command]
fn update_pump_config(
    app: tauri::AppHandle,
    name: String,
    pump: PumpConfig,
    original_name: Option<String>,
) -> Result<Value, String> {

    let mut config = read_config(&app)?;
    let pumps = devices_object(&mut config, "Pumps")?;

    if let Some(orig) = &original_name {
        if orig != &name {
            pumps.remove(orig);
        }
    }

    let pump_value =
        serde_json::to_value(&pump)
            .map_err(|e| format!("Failed to serialize pump: {e}"))?;

    pumps.insert(name, pump_value);

    write_config(&app, &config)?;

    get_device_configs(&config, "Pumps")
}


#[tauri::command]
fn delete_pump_config(
    app: tauri::AppHandle,
    name: String,
) -> Result<Value, String> {

    let mut config = read_config(&app)?;
    let pumps = devices_object(&mut config, "Pumps")?;

    pumps.remove(&name);

    write_config(&app, &config)?;

    get_device_configs(&config, "Pumps")
}


/// Imports multiple pump configurations.
/// Existing names are skipped to avoid overwriting.
#[tauri::command]
fn import_pump_configs(
    app: tauri::AppHandle,
    pumps: HashMap<String, PumpConfig>,
) -> Result<ImportResult, String> {

    let mut config = read_config(&app)?;
    let existing = devices_object(&mut config, "Pumps")?;

    let mut added = Vec::new();
    let mut skipped = Vec::new();

    let mut entries: Vec<(String, PumpConfig)> =
        pumps.into_iter().collect();

    entries.sort_by(|a, b| a.0.cmp(&b.0));


    for (name, pump) in entries {

        if existing.contains_key(&name) {
            skipped.push(name);
            continue;
        }


        let pump_value =
            serde_json::to_value(&pump)
                .map_err(|e| {
                    format!("Failed to serialize pump \"{name}\": {e}")
                })?;


        existing.insert(name.clone(), pump_value);
        added.push(name);
    }


    write_config(&app, &config)?;


    let updated_pumps =
        get_device_configs(&config, "Pumps")?;


    Ok(ImportResult {
        added,
        skipped,
        pumps: updated_pumps,
    })
}



// -------------------------
// Sidecar (v9-sidecar) execution
// -------------------------

/// Result of a single one-shot sidecar invocation, surfaced to the frontend.
#[derive(Debug, Serialize)]
pub struct SidecarResult {
    success: bool,
    code: Option<i32>,
    stdout: String,
    stderr: String,
}

/// Optional pump action parameters. Only the flags relevant to the chosen
/// `option` need to be provided; the rest are omitted from the CLI call.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PumpAction {
    /// One of: initialize, withdraw, inject, full-injection, empty, debubble,
    /// clean, stop, query-position
    option: String,
    rate: Option<f64>,
    speed: Option<i64>,
    position: Option<i64>,
    duration: Option<i64>,
    injection_time: Option<f64>,
    syringe_volume: Option<f64>,
    syringe_size: Option<i64>,
}

/// Build the shared serial-connection flags from a device's SerialConfig.
fn serial_args(cfg: &SerialConfig) -> Vec<String> {
    vec![
        "--port".into(),
        cfg.port.clone(),
        "--baudrate".into(),
        cfg.baudrate.to_string(),
        "--bytesize".into(),
        cfg.bytesize.to_string(),
        "--parity".into(),
        cfg.parity.clone(),
        "--stopbits".into(),
        cfg.stopbits.to_string(),
        "--timeout".into(),
        cfg.timeout.to_string(),
        "--xonxoff".into(),
        cfg.xonxoff.to_string(),
        "--rtscts".into(),
        cfg.rtscts.to_string(),
        "--dsrdtr".into(),
        cfg.dsrdtr.to_string(),
        "--write-timeout".into(),
        cfg.write_timeout.to_string(),
    ]
}

/// Spawn the bundled v9-sidecar binary with the given args and collect output.
async fn run_sidecar(app: &tauri::AppHandle, args: Vec<String>) -> Result<SidecarResult, String> {
    let command = app
        .shell()
        .sidecar("v9-sidecar")
        .map_err(|e| format!("Failed to locate v9-sidecar: {e}"))?
        .args(args);

    let output = command
        .output()
        .await
        .map_err(|e| format!("Failed to run v9-sidecar: {e}"))?;

    Ok(SidecarResult {
        success: output.status.success(),
        code: output.status.code(),
        stdout: String::from_utf8_lossy(&output.stdout).to_string(),
        stderr: String::from_utf8_lossy(&output.stderr).to_string(),
    })
}

/// Move a selector valve.
///
/// Provide `mode` for the 10-port main valve (sample|air|solvent), or
/// `position` for a raw position (e.g. a 28-port valve port resolved from the
/// valve's `Connections` map on the frontend).
#[tauri::command]
async fn move_valve(
    app: tauri::AppHandle,
    name: String,
    valve: SelectorValveConfig,
    mode: Option<String>,
    position: Option<u32>,
) -> Result<SidecarResult, String> {
    let mut args = vec!["valve".to_string()];
    args.extend(serial_args(&valve.serial));
    args.push("--name".into());
    args.push(name);
    args.push("--positions".into());
    args.push(valve.positions.to_string());

    match (mode, position) {
        (Some(m), _) => {
            args.push("--mode".into());
            args.push(m);
        }
        (None, Some(p)) => {
            args.push("--position".into());
            args.push(p.to_string());
        }
        (None, None) => return Err("move_valve requires either `mode` or `position`".into()),
    }

    run_sidecar(&app, args).await
}

/// Run a single pump action.
#[tauri::command]
async fn run_pump(
    app: tauri::AppHandle,
    name: String,
    pump: PumpConfig,
    action: PumpAction,
) -> Result<SidecarResult, String> {
    let mut args = vec!["pump".to_string()];
    args.extend(serial_args(&pump.serial));
    args.push("--name".into());
    args.push(name);
    args.push("--pump-num".into());
    args.push(pump.pump_number.to_string());
    args.push("--option".into());
    args.push(action.option);

    if let Some(v) = action.rate {
        args.push("--rate".into());
        args.push(v.to_string());
    }
    if let Some(v) = action.speed {
        args.push("--speed".into());
        args.push(v.to_string());
    }
    if let Some(v) = action.position {
        args.push("--position".into());
        args.push(v.to_string());
    }
    if let Some(v) = action.duration {
        args.push("--duration".into());
        args.push(v.to_string());
    }
    if let Some(v) = action.injection_time {
        args.push("--injection-time".into());
        args.push(v.to_string());
    }
    if let Some(v) = action.syringe_volume {
        args.push("--syringe-volume".into());
        args.push(v.to_string());
    }
    if let Some(v) = action.syringe_size {
        args.push("--syringe-size".into());
        args.push(v.to_string());
    }

    run_sidecar(&app, args).await
}

/// Run a multi-step pump/valve routine ported from V9.
///
/// The routine runs inside the sidecar over persistent serial connections
/// (preserving V9 ordering/timing/threading). `payload` carries whole device
/// configs and routine parameters and is forwarded verbatim as JSON to the
/// sidecar's `routine --payload` flag. The frontend assembles the payload from
/// the device configs it already holds. Supported routines: `switch-sample`,
/// `jar-switch`, `flow-rate`.
#[tauri::command]
async fn run_routine(
    app: tauri::AppHandle,
    routine: String,
    payload: Value,
) -> Result<SidecarResult, String> {
    let payload_str = serde_json::to_string(&payload)
        .map_err(|e| format!("Failed to serialize routine payload: {e}"))?;

    let args = vec![
        "routine".to_string(),
        "--routine".into(),
        routine,
        "--payload".into(),
        payload_str,
    ];

    run_sidecar(&app, args).await
}

/// Parameters for a viscosity/density sensor run, forwarded to the sidecar's
/// `vd` subcommand. Every field except `action` is optional; omitted fields
/// fall back to the sidecar's own defaults (which mirror the "VD Routine"
/// config). `action` is `measure` or `detect`.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct VdParams {
    action: String,
    serial: Option<String>,
    verbose: Option<bool>,
    track_impedance: Option<bool>,
    peak_center_reference: Option<f64>,
    peak_center_tolerance: Option<f64>,
    peak_width_reference: Option<f64>,
    peak_width_tolerance: Option<f64>,
    measurements: Option<i64>,
    batch_size: Option<i64>,
    viscosity_std: Option<f64>,
    density_std: Option<f64>,
    warmup: Option<f64>,
    max_samples: Option<i64>,
}

/// Run (or detect) the XtalX viscosity/density sensor via the sidecar.
///
/// The sidecar prints a single JSON object on stdout (means, std devs and the
/// raw per-reading samples for `measure`; the serial number for `detect`),
/// which the frontend parses out of `SidecarResult.stdout`.
#[tauri::command]
async fn run_vd(app: tauri::AppHandle, params: VdParams) -> Result<SidecarResult, String> {
    let mut args = vec!["vd".to_string(), "--action".into(), params.action];

    if let Some(v) = params.serial {
        args.push("--serial".into());
        args.push(v);
    }
    if let Some(v) = params.verbose {
        args.push("--verbose".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.track_impedance {
        args.push("--track-impedance".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.peak_center_reference {
        args.push("--peak-center-reference".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.peak_center_tolerance {
        args.push("--peak-center-tolerance".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.peak_width_reference {
        args.push("--peak-width-reference".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.peak_width_tolerance {
        args.push("--peak-width-tolerance".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.measurements {
        args.push("--measurements".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.batch_size {
        args.push("--batch-size".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.viscosity_std {
        args.push("--viscosity-std".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.density_std {
        args.push("--density-std".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.warmup {
        args.push("--warmup".into());
        args.push(v.to_string());
    }
    if let Some(v) = params.max_samples {
        args.push("--max-samples".into());
        args.push(v.to_string());
    }

    run_sidecar(&app, args).await
}

/// Run a heat-capacity (HC) measurement via the sidecar's `hc` subcommand.
///
/// `payload` carries the sample/reference pump configs, the DAQ config and the
/// experiment / stabilization / fluid parameters (assembled on the frontend
/// from the device configs it already holds), and is forwarded verbatim as JSON
/// to the sidecar's `hc --payload` flag. The sidecar prints a single JSON
/// result object on stdout (per-step stabilization outcomes, the voltage trace
/// and the regressed heat capacity), which the frontend parses out of
/// `SidecarResult.stdout`.
#[tauri::command]
async fn run_hc(app: tauri::AppHandle, payload: Value) -> Result<SidecarResult, String> {
    let payload_str = serde_json::to_string(&payload)
        .map_err(|e| format!("Failed to serialize HC payload: {e}"))?;

    let args = vec![
        "hc".to_string(),
        "--payload".into(),
        payload_str,
    ];

    run_sidecar(&app, args).await
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}



#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {

    tauri::Builder::default()

        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())

        .setup(|app| {
            ensure_config_exists(&app.handle())?;
            Ok(())
        })

        .invoke_handler(
            tauri::generate_handler![
                greet,

                // Generic device getters
                get_pump_configs,
                get_valve_configs,
                get_daq_configs,
                get_vd_config,

                // Pump operations
                pump_config_exists,
                update_pump_config,
                delete_pump_config,
                import_pump_configs,

                // Sidecar hardware control
                move_valve,
                run_pump,
                run_routine,
                run_vd,
                run_hc
            ]
        )

        .run(tauri::generate_context!())

        .expect("error while running tauri application");
}