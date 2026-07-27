import json

from loguru import logger

from device_discovery import DeviceDiscovery, DeviceManager

"""
Auto Device Setup Example
Shows how to use device discovery to automatically configure lab equipment
"""


def main():
    
    logger.info("Automatic Laboratory Device Setup")
    logger.info("=" * 50)
    
    # Discover all connected devices
    logger.info("\n1. Discovering connected devices...")
    discovery = DeviceDiscovery()
    devices = discovery.scan_all_devices()
    
    logger.info(discovery.get_device_summary())
    
    # Auto-configure devices
    logger.info("\n2. Auto-configuring devices...")
    config = discovery.auto_configure_devices()
    
    # Show configuration
    logger.info("\n3. Device Configuration:")
    logger.info(json.dumps(config, indent=2, default=str))
    
    # Save configuration for future use
    discovery.save_configuration('my_lab_config.json')
    logger.info("\n4. Configuration saved to 'my_lab_config.json'")
    
    # Example of using discovered devices
    logger.info("\n5. Device Usage Examples:")
    
    # Show how to use pumps
    if config['pumps']:
        logger.info("\nHamilton Pumps detected:")
        for i, pump in enumerate(config['pumps']):
            logger.info(f"  Pump {i+1}: {pump['port']} at {pump['baudrate']} baud")
            logger.info(f"    Usage: SerialDevice('{pump['port']}', {pump['baudrate']})")
    
    # Show how to use valves
    if config['valves']:
        logger.info("\nSelector Valves detected:")
        for i, valve in enumerate(config['valves']):
            logger.info(f"  Valve {i+1}: {valve['port']} at {valve['baudrate']} baud")
            logger.info(f"    Usage: SelectorValve('{valve['port']}', {valve['baudrate']})")
    
    # Show how to use DAQ
    if config['daq']:
        logger.info("\nDAQ Devices detected:")
        for i, daq in enumerate(config['daq']):
            logger.info(f"  DAQ {i+1}: {daq['name']} ({daq['type']})")
            if daq['ai_channels']:
                logger.info(f"    AI Channel: {daq['ai_channels'][0]}")
                logger.info(f"    Usage: DAQDevice('{daq['ai_channels'][0]}', 3)")
    
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
    
    logger.info("Auto-initialization code saved to 'auto_device_init.py'")
    return init_code

def test_device_connections():
    """Test connections to all discovered devices."""
    
    logger.info("\nTesting device connections...")
    discovery = DeviceDiscovery()
    discovery.scan_all_devices()
    config = discovery.auto_configure_devices()
    
    # Test pump connections
    logger.info("\nTesting pump connections:")
    for pump in config.get('pumps', []):
        success = discovery.test_device_connection(pump['port'], pump['baudrate'])
        status = "✓ OK" if success else "✗ FAILED"
        logger.info(f"  {pump['name']} on {pump['port']}: {status}")
    
    # Test valve connections
    logger.info("\nTesting valve connections:")
    for valve in config.get('valves', []):
        success = discovery.test_device_connection(valve['port'], valve['baudrate'])
        status = "✓ OK" if success else "✗ FAILED"
        logger.info(f"  {valve['name']} on {valve['port']}: {status}")
    
    # Test DAQ availability
    logger.info("\nTesting DAQ devices:")
    for daq in config.get('daq', []):
        logger.info(f"  {daq['name']}: ✓ Available")

if __name__ == "__main__":
    # Run main discovery
    config = main()
    
    # Generate dynamic initialization code
    logger.info("\n" + "=" * 50)
    create_dynamic_device_config()
    
    # Test connections
    logger.info("\n" + "=" * 50)
    test_device_connections()