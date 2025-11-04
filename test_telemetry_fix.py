"""
Test script to verify telemetry change flag behavior

This script tests that change flags work correctly by directly
testing the clear methods.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry

def test_change_flag_clear_methods():
    """Test that change flag clear methods work"""
    
    # Create telemetry instance (not connected)
    config = {
        'connection_string': 'udp:127.0.0.1:14550',
        'auto_detect': False
    }
    
    telem = MAVLinkTelemetry(config)
    
    print("Testing change flag clear methods...")
    print("=" * 60)
    
    # Test 1: Armed changed flag
    print("\nTest 1: Armed change flag")
    print("-" * 60)
    telem._armed_changed = True
    print(f"Set _armed_changed to True: {telem._armed_changed}")
    
    telem.clear_armed_changed()
    print(f"After clear_armed_changed(): {telem._armed_changed}")
    
    test1_pass = (telem._armed_changed == False)
    print(f"Result: {'✓ PASS' if test1_pass else '❌ FAIL'}")
    
    # Test 2: Flight mode changed flag
    print("\nTest 2: Flight mode change flag")
    print("-" * 60)
    telem._flight_mode_changed = True
    print(f"Set _flight_mode_changed to True: {telem._flight_mode_changed}")
    
    telem.clear_flight_mode_changed()
    print(f"After clear_flight_mode_changed(): {telem._flight_mode_changed}")
    
    test2_pass = (telem._flight_mode_changed == False)
    print(f"Result: {'✓ PASS' if test2_pass else '❌ FAIL'}")
    
    # Test 3: Property accessors
    print("\nTest 3: Property accessors")
    print("-" * 60)
    telem._armed = True
    telem._armed_changed = True
    telem._flight_mode = "GUIDED"
    telem._flight_mode_changed = True
    
    print(f"Set armed=True, armed_changed=True")
    print(f"Set flight_mode='GUIDED', flight_mode_changed=True")
    print()
    print(f"telem.armed property: {telem.armed}")
    print(f"telem.armed_changed property: {telem.armed_changed}")
    print(f"telem.flight_mode property: {telem.flight_mode}")
    print(f"telem.flight_mode_changed property: {telem.flight_mode_changed}")
    
    test3_pass = (
        telem.armed == True and
        telem.armed_changed == True and
        telem.flight_mode == "GUIDED" and
        telem.flight_mode_changed == True
    )
    print(f"Result: {'✓ PASS' if test3_pass else '❌ FAIL'}")
    
    # Test 4: Clearing via properties
    print("\nTest 4: Clearing flags via properties")
    print("-" * 60)
    print("Before clearing:")
    print(f"  armed_changed: {telem.armed_changed}")
    print(f"  flight_mode_changed: {telem.flight_mode_changed}")
    
    telem.clear_armed_changed()
    telem.clear_flight_mode_changed()
    
    print("After clearing:")
    print(f"  armed_changed: {telem.armed_changed}")
    print(f"  flight_mode_changed: {telem.flight_mode_changed}")
    print("State should remain:")
    print(f"  armed: {telem.armed}")
    print(f"  flight_mode: {telem.flight_mode}")
    
    test4_pass = (
        telem.armed_changed == False and
        telem.flight_mode_changed == False and
        telem.armed == True and
        telem.flight_mode == "GUIDED"
    )
    print(f"Result: {'✓ PASS' if test4_pass else '❌ FAIL'}")
    
    # Final results
    print("\n" + "=" * 60)
    print("TEST SUMMARY:")
    print("=" * 60)
    print(f"Test 1 (clear_armed_changed):      {'✓ PASS' if test1_pass else '❌ FAIL'}")
    print(f"Test 2 (clear_flight_mode_changed): {'✓ PASS' if test2_pass else '❌ FAIL'}")
    print(f"Test 3 (property accessors):        {'✓ PASS' if test3_pass else '❌ FAIL'}")
    print(f"Test 4 (clearing preserves state):  {'✓ PASS' if test4_pass else '❌ FAIL'}")
    
    all_pass = test1_pass and test2_pass and test3_pass and test4_pass
    
    print("\n" + "=" * 60)
    if all_pass:
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("Change flag clear methods work correctly!")
        print("\nThe fix in get_flattened_telemetry() that calls these")
        print("clear methods will properly reset change flags after reading.")
    else:
        print("❌❌❌ SOME TESTS FAILED ❌❌❌")
        print("Change flag behavior needs fixing!")
    print("=" * 60)
    
    return all_pass


if __name__ == "__main__":
    success = test_change_flag_clear_methods()
    sys.exit(0 if success else 1)
