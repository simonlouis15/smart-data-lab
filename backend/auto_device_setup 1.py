"""
Auto Device Setup Example
Shows how to use device discovery to automatically configure lab equipment
"""

from device_discovery import DeviceDiscovery, DeviceManager
import json

def main():
    """Main example showing automatic device discovery and setup."""
    
    print("Automatic Laboratory Device Setup")
    print("=" * 50)
    
    # Step 1: Discover all connected devices
    print("\n1. Discovering connected devices...")
    discovery = DeviceDiscovery()
    devices = discovery.scan_all_devices()
    
    print(discovery.get_device_summary())
    
    # Step 2: Auto-configure devices
    print("\n2. Auto-configuring devices...")
    config = discovery.auto_configure_devices()
    
    # Step 3: Show configuration
    print("\n3. Device Configuration:")
    print(json.dumps(config, indent=2, default=str))
    
    # Step 4: Save configuration for future use
    discovery.save_configuration('my_lab_config.json')
    print("\n4. Configuration saved to 'my_lab_config.json'")
    
    # Step 5: Example of using discovered devices
    print("\n5. Device Usage Examples:")
    
    # Show how to use pumps
    if config['pumps']:
        print("\nHamilton Pumps detected:")
        for i, pump in enumerate(config['pumps']):
            print(f"  Pump {i+1}: {pump['port']} at {pump['baudrate']} baud")
            print(f"    Usage: SerialDevice('{pump['port']}', {pump['baudrate']})")
    
    # Show how to use valves
    if config['valves']:
        print("\nSelector Valves detected:")
        for i, valve in enumerate(config['valves']):
            print(f"  Valve {i+1}: {valve['port']} at {valve['baudrate']} baud")
            print(f"    Usage: SelectorValve('{valve['port']}', {valve['baudrate']})")
    
    # Show how to use DAQ
    if config['daq']:
        print("\nDAQ Devices detected:")
        for i, daq in enumerate(config['daq']):
            print(f"  DAQ {i+1}: {daq['name']} ({daq['type']})")
            if daq['ai_channels']:
                print(f"    AI Channel: {daq['ai_channels'][0]}")
                print(f"    Usage: DAQDevice('{daq['ai_channels'][0]}', 3)")
    
    return config

def create_dynamic_device_config():
    """Create a configuration that can be used to dynamically initialize devices."""
    
    manager = DeviceManager()
    config = manager.initialize_all_devices()
    
    # Generate Python code for device initialization
    init_code = []
    init_code.append("# Auto-generated device initialization code")
    init_code.append("from device_discovery import DeviceManager")
    init_code.append("")
    
    # Pumps
    if config.get('pumps'):
        init_code.append("# Hamilton Pumps")
        for i, pump in enumerate(config['pumps']):
            init_code.append(f"pump_{i+1} = SerialDevice('{pump['port']}', {pump['baudrate']}, 'Pump_{i+1}')")
        init_code.append("")
    
    # Valves
    if config.get('valves'):
        init_code.append("# Selector Valves")
        for i, valve in enumerate(config['valves']):
            init_code.append(f"valve_{i+1} = SelectorValve('{valve['port']}', {valve['baudrate']})")
        init_code.append("")
    
    # DAQ
    if config.get('daq'):
        init_code.append("# DAQ Devices")
        for i, daq in enumerate(config['daq']):
            if daq.get('ai_channels'):
                init_code.append(f"daq_{i+1} = DAQDevice('{daq['ai_channels'][0]}', 3)")
        init_code.append("")
    
    # Save the initialization code
    with open('auto_device_init.py', 'w') as f:
        f.write('\n'.join(init_code))
    
    print("Auto-initialization code saved to 'auto_device_init.py'")
    return init_code

def test_device_connections():
    """Test connections to all discovered devices."""
    
    print("\nTesting device connections...")
    discovery = DeviceDiscovery()
    discovery.scan_all_devices()
    config = discovery.auto_configure_devices()
    
    # Test pump connections
    print("\nTesting pump connections:")
    for pump in config.get('pumps', []):
        success = discovery.test_device_connection(pump['port'], pump['baudrate'])
        status = "✓ OK" if success else "✗ FAILED"
        print(f"  {pump['name']} on {pump['port']}: {status}")
    
    # Test valve connections
    print("\nTesting valve connections:")
    for valve in config.get('valves', []):
        success = discovery.test_device_connection(valve['port'], valve['baudrate'])
        status = "✓ OK" if success else "✗ FAILED"
        print(f"  {valve['name']} on {valve['port']}: {status}")
    
    # Test DAQ availability
    print("\nTesting DAQ devices:")
    for daq in config.get('daq', []):
        print(f"  {daq['name']}: ✓ Available")

if __name__ == "__main__":
    # Run main discovery
    config = main()
    
    # Generate dynamic initialization code
    print("\n" + "=" * 50)
    create_dynamic_device_config()
    
    # Test connections
    print("\n" + "=" * 50)
    test_device_connections()