import argparse
import sys
import os

# Add project root to path to allow imports from app
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_root)

from app.services.update_manager import update_manager

def main():
    parser = argparse.ArgumentParser(description="Revert all applied updates.")
    # No arguments needed anymore
    args = parser.parse_args()
    
    print("Attempting to revert all successfully applied updates...")
    
    result = update_manager.revert_all_updates()
    
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    else:
        print("Revert process finished!")
        print(f"  Reverted and removed: {result['reverted_and_removed_count']}")
        print(f"  Failed to revert: {result['failed_to_revert_count']}")
        
        if result.get('details'):
            print("Details:")
            for detail in result['details']:
                reason = f" (Reason: {detail['reason']})" if 'reason' in detail else ""
                print(f"  - Suggestion {detail['suggestion_id']}: {detail['status']}{reason}")

if __name__ == "__main__":
    main() 