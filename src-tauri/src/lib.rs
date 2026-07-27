use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use tauri::Manager;

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

                // Pump operations
                pump_config_exists,
                update_pump_config,
                delete_pump_config,
                import_pump_configs
            ]
        )

        .run(tauri::generate_context!())

        .expect("error while running tauri application");
}