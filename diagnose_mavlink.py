"""
Quick MAVLink Connection Diagnostic

Quickly checks if ArduPilot SITL or hardware is available and responsive.
Useful for troubleshooting connection issues before running full tests.
"""

import sys
import socket
import time
from pymavlink import mavutil


def check_udp_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if UDP port is reachable.
    
    Args:
        host: Host address
        port: Port number
        timeout: Timeout in seconds
        
    Returns:
        True if port appears to be open
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        # For UDP, we can't really "connect", but we can try to send/receive
        sock.sendto(b'', (host, port))
        return True
    except Exception as e:
        return False
    finally:
        sock.close()


def check_tcp_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if TCP port is open.
    
    Args:
        host: Host address
        port: Port number
        timeout: Timeout in seconds
        
    Returns:
        True if port is open
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def quick_heartbeat_check(connection_string: str, timeout: int = 5) -> dict:
    """
    Quick check for MAVLink heartbeat.
    
    Args:
        connection_string: MAVLink connection string
        timeout: Timeout in seconds
        
    Returns:
        Dictionary with results
    """
    result = {
        'connected': False,
        'system_id': None,
        'component_id': None,
        'autopilot': None,
        'vehicle_type': None,
        'flight_mode': None,
        'armed': False,
        'error': None
    }
    
    try:
        conn = mavutil.mavlink_connection(connection_string, timeout=timeout)
        msg = conn.wait_heartbeat(timeout=timeout)
        
        if msg:
            result['connected'] = True
            result['system_id'] = conn.target_system
            result['component_id'] = conn.target_component
            result['autopilot'] = msg.autopilot
            result['vehicle_type'] = msg.type
            result['armed'] = bool(msg.base_mode & 128)  # MAV_MODE_FLAG_SAFETY_ARMED
            
            # Try to decode flight mode
            copter_modes = {
                0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
                4: "GUIDED", 5: "LOITER", 6: "RTL", 9: "LAND"
            }
            result['flight_mode'] = copter_modes.get(msg.custom_mode, f"CUSTOM({msg.custom_mode})")
        else:
            result['error'] = "No heartbeat received"
        
        conn.close()
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def diagnose_connection(connection_string: str = 'udp:127.0.0.1:14550'):
    """
    Diagnose MAVLink connection issues.
    
    Args:
        connection_string: Connection string to test
    """
    print("=" * 70)
    print("MAVLink Connection Diagnostic")
    print("=" * 70)
    print()
    print(f"Testing connection: {connection_string}")
    print()
    
    # Parse connection string
    if connection_string.startswith('udp:'):
        protocol = 'UDP'
        parts = connection_string[4:].split(':')
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 14550
    elif connection_string.startswith('tcp:'):
        protocol = 'TCP'
        parts = connection_string[4:].split(':')
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 5760
    else:
        protocol = 'SERIAL'
        host = None
        port = None
    
    print(f"Protocol: {protocol}")
    if host:
        print(f"Host:     {host}")
        print(f"Port:     {port}")
    print()
    
    # Step 1: Check network connectivity (if UDP/TCP)
    if protocol in ['UDP', 'TCP']:
        print("Step 1: Checking network port...")
        if protocol == 'UDP':
            port_open = check_udp_port(host, port)
        else:
            port_open = check_tcp_port(host, port)
        
        if port_open:
            print(f"  ✓ Port {port} appears to be accessible")
        else:
            print(f"  ⚠  Port {port} may not be accessible")
            print(f"     (Note: This is normal for UDP if SITL not running)")
        print()
    
    # Step 2: Try MAVLink heartbeat
    print("Step 2: Checking for MAVLink heartbeat...")
    result = quick_heartbeat_check(connection_string, timeout=10)
    
    if result['connected']:
        print("  ✅ HEARTBEAT RECEIVED!")
        print()
        print("  Connection Details:")
        print(f"    System ID:     {result['system_id']}")
        print(f"    Component ID:  {result['component_id']}")
        print(f"    Autopilot:     {result['autopilot']}")
        print(f"    Vehicle Type:  {result['vehicle_type']}")
        print(f"    Flight Mode:   {result['flight_mode']}")
        print(f"    Armed:         {result['armed']}")
        print()
        print("  ✅ CONNECTION IS WORKING!")
        print()
        print("  You can now run the full tests:")
        print("    .\\venv\\Scripts\\python.exe test_mavlink_connection.py")
        print("    .\\venv\\Scripts\\python.exe test_telemetry_integration.py")
        return True
    else:
        print("  ❌ NO HEARTBEAT RECEIVED")
        print()
        print(f"  Error: {result['error']}")
        print()
        print("  Troubleshooting steps:")
        print()
        print("  1. Make sure ArduPilot SITL is running:")
        print("     WSL: sim_vehicle.py -v ArduCopter -f gazebo-iris --console")
        print()
        print("  2. Check the connection string matches SITL output:")
        print("     Look for: 'Awaiting connections via udp:127.0.0.1:14550'")
        print()
        print("  3. Try different connection strings:")
        print("     - udp:127.0.0.1:14550 (default SITL)")
        print("     - tcp:127.0.0.1:5762  (MAVProxy forward)")
        print("     - udp:127.0.0.1:14551 (alternative)")
        print()
        print("  4. Check firewall settings (Windows Firewall may block)")
        print()
        print("  5. If using WSL, ensure port forwarding is working:")
        print("     PowerShell: netsh interface portproxy show all")
        print()
        return False


def test_multiple_connections():
    """Test multiple common connection strings."""
    print("=" * 70)
    print("Testing Multiple Common Connection Strings")
    print("=" * 70)
    print()
    
    connections = [
        'udp:127.0.0.1:14550',  # Default SITL
        'udp:127.0.0.1:14551',  # Alternative
        'tcp:127.0.0.1:5762',   # MAVProxy
        'tcp:127.0.0.1:5763',   # Alternative MAVProxy
    ]
    
    for conn_str in connections:
        print(f"Testing: {conn_str}...", end=' ')
        sys.stdout.flush()
        
        result = quick_heartbeat_check(conn_str, timeout=3)
        
        if result['connected']:
            print(f"✅ CONNECTED (System {result['system_id']}, {result['flight_mode']})")
        else:
            print(f"❌ No response")
    
    print()


def main():
    """Main diagnostic function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Diagnose MAVLink connection')
    parser.add_argument('connection', nargs='?', default='udp:127.0.0.1:14550',
                       help='Connection string (default: udp:127.0.0.1:14550)')
    parser.add_argument('--scan', action='store_true',
                       help='Scan multiple common connection strings')
    
    args = parser.parse_args()
    
    if args.scan:
        test_multiple_connections()
    else:
        success = diagnose_connection(args.connection)
        return 0 if success else 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
