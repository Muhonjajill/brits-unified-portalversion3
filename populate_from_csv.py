"""
===============================================================================
COMPREHENSIVE ZONE AND REGION POPULATION SCRIPT
===============================================================================

This script reads a CSV file containing terminal data and:
1. Creates regions if they don't exist
2. Creates zones within their proper regions
3. Assigns terminals to correct region-zone combinations
4. Cleans up any orphaned zones
5. Provides detailed verification and reporting

USAGE:
------
1. Update the CSV_FILE_PATH variable below with your CSV file location
2. Run in Django shell:
   python manage.py shell < populate_from_csv.py
   
   OR copy-paste into Django shell:
   python manage.py shell
   [paste entire script]

CSV FORMAT REQUIRED:
-------------------
Your CSV must have these columns:
- id: Terminal ID
- customer: Customer name
- branch_name: Branch name
- cdm_name: CDM name
- serial_number: Serial number
- model: Model name
- region: Region name (e.g., "Nairobi Region")
- zone: Zone name (e.g., "Zone A")

AUTHOR: Godbless Okaka
DATE: January 2026
===============================================================================
"""

from core.models import Zone, Region, Terminal
import csv
from collections import defaultdict
from django.db import transaction

# ============================================================================
# CONFIGURATION - UPDATE THIS PATH TO YOUR CSV FILE
# ============================================================================
CSV_FILE_PATH = '/home/gokaka/moved/terminals.csv'

# ============================================================================
# SCRIPT START
# ============================================================================

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80)

def print_section(text):
    """Print a formatted section header"""
    print(f"\n{text}")
    print("-" * 80)

def read_csv_data(csv_path):
    """Read and parse CSV data into a structured format"""
    data = defaultdict(lambda: defaultdict(list))
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                region_name = row['region'].strip()
                zone_name = row['zone'].strip()
                
                data[region_name][zone_name].append({
                    'id': row['id'],
                    'customer': row['customer'],
                    'branch_name': row['branch_name'],
                    'cdm_name': row['cdm_name'],
                    'serial_number': row['serial_number'],
                    'model': row['model']
                })
        
        return data, None
    
    except FileNotFoundError:
        return None, f"CSV file not found at: {csv_path}"
    except KeyError as e:
        return None, f"Missing required column in CSV: {e}"
    except Exception as e:
        return None, f"Error reading CSV: {str(e)}"

def create_regions(region_names):
    """Create or get regions"""
    stats = {'created': 0, 'existing': 0}
    regions = {}
    
    for region_name in region_names:
        region, created = Region.objects.get_or_create(name=region_name)
        regions[region_name] = region
        
        if created:
            stats['created'] += 1
            print(f"  ✓ Created: {region_name} (ID: {region.id})")
        else:
            stats['existing'] += 1
            print(f"  ✓ Found: {region_name} (ID: {region.id})")
    
    return regions, stats

def create_zones_and_assign_terminals(csv_data):
    """Create zones in their regions and assign terminals"""
    stats = {
        'zones_created': 0,
        'zones_existing': 0,
        'terminals_updated': 0,
        'terminals_created': 0
    }
    
    with transaction.atomic():
        for region_name, zones_dict in csv_data.items():
            region = Region.objects.get(name=region_name)
            print(f"\n  Processing {region_name}:")
            
            for zone_name, terminals_list in zones_dict.items():
                # Get or create zone with proper region
                zone, created = Zone.objects.get_or_create(
                    name=zone_name,
                    region=region
                )
                
                if created:
                    stats['zones_created'] += 1
                    print(f"    ✓ Created zone: {zone_name} (ID: {zone.id})")
                else:
                    stats['zones_existing'] += 1
                    print(f"    ✓ Found zone: {zone_name} (ID: {zone.id})")
                
                # Assign terminals to this zone
                for terminal_data in terminals_list:
                    try:
                        # Try to find existing terminal
                        terminal = Terminal.objects.get(id=terminal_data['id'])
                        terminal.region = region
                        terminal.zone = zone
                        terminal.save(update_fields=['region', 'zone'])
                        stats['terminals_updated'] += 1
                        
                    except Terminal.DoesNotExist:
                        # Create new terminal if it doesn't exist
                        Terminal.objects.create(
                            id=terminal_data['id'],
                            customer=terminal_data['customer'],
                            branch_name=terminal_data['branch_name'],
                            cdm_name=terminal_data['cdm_name'],
                            serial_number=terminal_data['serial_number'],
                            model=terminal_data['model'],
                            region=region,
                            zone=zone
                        )
                        stats['terminals_created'] += 1
                
                print(f"      → Assigned {len(terminals_list)} terminals")
    
    return stats

def cleanup_orphaned_zones():
    """Remove zones that have no terminals and no region"""
    orphaned = []
    
    # Find zones with no terminals OR no region
    for zone in Zone.objects.all():
        terminal_count = Terminal.objects.filter(zone=zone).count()
        if terminal_count == 0 or zone.region is None:
            orphaned.append(zone)
    
    if orphaned:
        print(f"\n  Found {len(orphaned)} orphaned zones:")
        with transaction.atomic():
            for zone in orphaned:
                region_name = zone.region.name if zone.region else "No Region"
                terminal_count = Terminal.objects.filter(zone=zone).count()
                print(f"    • {zone.name} in {region_name} ({terminal_count} terminals)")
                zone.delete()
        print(f"  ✓ Deleted {len(orphaned)} orphaned zones")
    else:
        print("  ✓ No orphaned zones found")
    
    return len(orphaned)

def verify_data():
    """Verify the data integrity"""
    print("\n📊 Database Structure:")
    
    for region in Region.objects.all().order_by('name'):
        zones = Zone.objects.filter(region=region).order_by('name')
        total_terminals = Terminal.objects.filter(region=region).count()
        
        print(f"\n  🌍 {region.name} ({total_terminals} terminals)")
        
        if zones.exists():
            for zone in zones:
                terminal_count = Terminal.objects.filter(zone=zone).count()
                print(f"    📍 {zone.name}: {terminal_count} terminals")
                
                # Show sample terminals
                sample_terminals = Terminal.objects.filter(zone=zone).order_by('branch_name')[:3]
                for terminal in sample_terminals:
                    print(f"       • {terminal.branch_name}")
                
                if terminal_count > 3:
                    print(f"       ... and {terminal_count - 3} more")
        else:
            print("    ⚠️  No zones found")
    
    # Check for issues
    print("\n🔍 Data Integrity Checks:")
    
    unassigned_zones = Terminal.objects.filter(zone__isnull=True).count()
    unassigned_regions = Terminal.objects.filter(region__isnull=True).count()
    zones_without_region = Zone.objects.filter(region__isnull=True).count()
    
    issues = []
    if unassigned_regions > 0:
        issues.append(f"  ⚠️  {unassigned_regions} terminals without regions")
    if unassigned_zones > 0:
        issues.append(f"  ⚠️  {unassigned_zones} terminals without zones")
    if zones_without_region > 0:
        issues.append(f"  ⚠️  {zones_without_region} zones without regions")
    
    if issues:
        print("\n".join(issues))
        return False
    else:
        print("  ✓ All terminals have regions and zones")
        print("  ✓ All zones are assigned to regions")
        return True

def print_summary(region_stats, zone_stats, orphaned_count, total_terminals):
    """Print final summary"""
    print_header("SUMMARY")
    
    print(f"""
Database Totals:
  • Regions: {Region.objects.count()}
  • Zones: {Zone.objects.count()}
  • Terminals: {Terminal.objects.count()}

Operations Performed:
  • Regions created: {region_stats['created']}
  • Regions found: {region_stats['existing']}
  • Zones created: {zone_stats['zones_created']}
  • Zones found: {zone_stats['zones_existing']}
  • Terminals updated: {zone_stats['terminals_updated']}
  • Terminals created: {zone_stats['terminals_created']}
  • Orphaned zones removed: {orphaned_count}

Total terminals processed: {total_terminals}
    """)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    
    print_header("ZONE & REGION POPULATION FROM CSV")
    print(f"\nCSV File: {CSV_FILE_PATH}")
    
    # Step 1: Read CSV
    print_section("STEP 1: Reading CSV Data")
    csv_data, error = read_csv_data(CSV_FILE_PATH)
    
    if error:
        print(f"  ✗ Error: {error}")
        print("\n💡 TIP: Update the CSV_FILE_PATH variable at the top of this script")
        return False
    
    total_terminals = sum(
        len(terminals)
        for zones in csv_data.values()
        for terminals in zones.values()
    )
    
    print(f"  ✓ Successfully read CSV")
    print(f"  ✓ Found {len(csv_data)} regions")
    print(f"  ✓ Found {total_terminals} terminals")
    
    # Display structure
    print("\n  CSV Structure:")
    for region_name in sorted(csv_data.keys()):
        zones = csv_data[region_name]
        print(f"    • {region_name}: {len(zones)} zones")
        for zone_name in sorted(zones.keys()):
            terminal_count = len(zones[zone_name])
            print(f"      └─ {zone_name}: {terminal_count} terminals")
    
    # Step 2: Create regions
    print_section("STEP 2: Creating/Updating Regions")
    regions, region_stats = create_regions(csv_data.keys())
    print(f"\n  ✓ Processed {len(regions)} regions")
    
    # Step 3: Create zones and assign terminals
    print_section("STEP 3: Creating Zones and Assigning Terminals")
    zone_stats = create_zones_and_assign_terminals(csv_data)
    print(f"\n  ✓ Processed {zone_stats['zones_created'] + zone_stats['zones_existing']} zones")
    print(f"  ✓ Processed {zone_stats['terminals_updated'] + zone_stats['terminals_created']} terminals")
    
    # Step 4: Cleanup
    print_section("STEP 4: Cleaning Up Orphaned Zones")
    orphaned_count = cleanup_orphaned_zones()
    
    # Step 5: Verification
    print_section("STEP 5: Verification")
    data_valid = verify_data()
    
    # Summary
    print_summary(region_stats, zone_stats, orphaned_count, total_terminals)
    
    if data_valid:
        print("✅ POPULATION COMPLETE!")
        print("\n💡 Next steps:")
        print("   1. Restart your Django server")
        print("   2. Clear your browser cache (Ctrl+Shift+R)")
        print("   3. Refresh your regions page")
        print("\n" + "=" * 80)
        return True
    else:
        print("⚠️  POPULATION COMPLETE WITH WARNINGS")
        print("   Please review the data integrity issues above.")
        print("\n" + "=" * 80)
        return False

# Run the script
if __name__ == "__main__":
    success = main()
else:
    # When pasted into Django shell
    success = main()
