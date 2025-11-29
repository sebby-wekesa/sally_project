#!/usr/bin/env python
"""
Database Migration Manager
Handles database schema versioning and migrations
"""

import os
import json
from datetime import datetime
from pathlib import Path
from app import app, db, ContactMessage

MIGRATIONS_DIR = Path(__file__).parent / 'migrations'
MIGRATIONS_DIR.mkdir(exist_ok=True)

MIGRATIONS_FILE = MIGRATIONS_DIR / 'migrations.json'


class Migration:
    """Base migration class"""
    
    version = None
    description = None
    
    def up(self):
        """Apply migration"""
        raise NotImplementedError
    
    def down(self):
        """Rollback migration"""
        raise NotImplementedError


class Migration_001_InitialSchema(Migration):
    """Initial schema creation with contact messages table"""
    
    version = '001'
    description = 'Initial schema with contact messages table'
    
    def up(self):
        """Create initial schema"""
        with app.app_context():
            db.create_all()
            print("✓ Created initial schema")
    
    def down(self):
        """Drop all tables"""
        with app.app_context():
            db.drop_all()
            print("✓ Dropped all tables")


class Migration_002_AddIndexes(Migration):
    """Add database indexes for performance"""
    
    version = '002'
    description = 'Add indexes to contact messages table'
    
    def up(self):
        """Add indexes"""
        with app.app_context():
            # Indexes are already defined in the model,
            # but this migration ensures they're created
            db.session.execute('CREATE INDEX IF NOT EXISTS ix_contact_messages_email ON contact_messages(email)')
            db.session.execute('CREATE INDEX IF NOT EXISTS ix_contact_messages_created_at ON contact_messages(created_at)')
            db.session.execute('CREATE INDEX IF NOT EXISTS ix_contact_messages_is_processed ON contact_messages(is_processed)')
            db.session.commit()
            print("✓ Created indexes")
    
    def down(self):
        """Remove indexes"""
        with app.app_context():
            db.session.execute('DROP INDEX IF EXISTS ix_contact_messages_email')
            db.session.execute('DROP INDEX IF EXISTS ix_contact_messages_created_at')
            db.session.execute('DROP INDEX IF EXISTS ix_contact_messages_is_processed')
            db.session.commit()
            print("✓ Dropped indexes")


class MigrationManager:
    """Manages database migrations"""
    
    MIGRATIONS = [
        Migration_001_InitialSchema,
        Migration_002_AddIndexes,
    ]
    
    @staticmethod
    def get_migration_history():
        """Get migration history from file"""
        if MIGRATIONS_FILE.exists():
            with open(MIGRATIONS_FILE, 'r') as f:
                return json.load(f)
        return {'applied': [], 'pending': []}
    
    @staticmethod
    def save_migration_history(history):
        """Save migration history to file"""
        with open(MIGRATIONS_FILE, 'w') as f:
            json.dump(history, f, indent=2, default=str)
    
    @staticmethod
    def mark_migration_applied(version):
        """Mark a migration as applied"""
        history = MigrationManager.get_migration_history()
        if version not in history['applied']:
            history['applied'].append(version)
            if version in history['pending']:
                history['pending'].remove(version)
            MigrationManager.save_migration_history(history)
    
    @staticmethod
    def mark_migration_pending(version):
        """Mark a migration as pending"""
        history = MigrationManager.get_migration_history()
        if version not in history['pending']:
            history['pending'].append(version)
            if version in history['applied']:
                history['applied'].remove(version)
            MigrationManager.save_migration_history(history)
    
    @staticmethod
    def get_pending_migrations():
        """Get list of pending migrations"""
        history = MigrationManager.get_migration_history()
        return [m for m in MigrationManager.MIGRATIONS if m.version not in history['applied']]
    
    @staticmethod
    def get_applied_migrations():
        """Get list of applied migrations"""
        history = MigrationManager.get_migration_history()
        return [m for m in MigrationManager.MIGRATIONS if m.version in history['applied']]
    
    @staticmethod
    def run_migration(migration_class):
        """Run a migration"""
        migration = migration_class()
        try:
            migration.up()
            MigrationManager.mark_migration_applied(migration.version)
            print(f"✓ Successfully applied migration {migration.version}: {migration.description}")
            return True
        except Exception as e:
            print(f"✗ Error applying migration {migration.version}: {str(e)}")
            return False
    
    @staticmethod
    def rollback_migration(migration_class):
        """Rollback a migration"""
        migration = migration_class()
        try:
            migration.down()
            MigrationManager.mark_migration_pending(migration.version)
            print(f"✓ Successfully rolled back migration {migration.version}: {migration.description}")
            return True
        except Exception as e:
            print(f"✗ Error rolling back migration {migration.version}: {str(e)}")
            return False
    
    @staticmethod
    def migrate_up(target_version=None):
        """Apply pending migrations"""
        pending = MigrationManager.get_pending_migrations()
        
        if not pending:
            print("✓ No pending migrations")
            return True
        
        print(f"\nApplying {len(pending)} pending migration(s)...")
        
        for migration_class in pending:
            if target_version and migration_class.version > target_version:
                break
            
            if not MigrationManager.run_migration(migration_class):
                return False
        
        print(f"\n✓ Successfully applied all pending migrations")
        return True
    
    @staticmethod
    def migrate_down(steps=1):
        """Rollback migrations"""
        applied = MigrationManager.get_applied_migrations()
        
        if not applied:
            print("✓ No applied migrations to rollback")
            return True
        
        # Reverse the order
        applied.reverse()
        
        print(f"\nRolling back {min(steps, len(applied))} migration(s)...")
        
        for i, migration_class in enumerate(applied):
            if i >= steps:
                break
            
            if not MigrationManager.rollback_migration(migration_class):
                return False
        
        print(f"\n✓ Successfully rolled back migrations")
        return True
    
    @staticmethod
    def status():
        """Show migration status"""
        applied = MigrationManager.get_applied_migrations()
        pending = MigrationManager.get_pending_migrations()
        
        print("\n" + "=" * 60)
        print("MIGRATION STATUS")
        print("=" * 60)
        
        if applied:
            print(f"\n✓ Applied Migrations ({len(applied)}):")
            for m in applied:
                print(f"  - {m.version}: {m.description}")
        else:
            print("\nNo applied migrations")
        
        if pending:
            print(f"\n⧗ Pending Migrations ({len(pending)}):")
            for m in pending:
                print(f"  - {m.version}: {m.description}")
        else:
            print("\n✓ All migrations applied")
        
        print("\n" + "=" * 60 + "\n")


def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python migrate.py [command]")
        print("\nCommands:")
        print("  up       - Apply pending migrations")
        print("  down     - Rollback last migration")
        print("  status   - Show migration status")
        print("  init     - Initialize migrations")
        return
    
    command = sys.argv[1]
    
    if command == 'up':
        MigrationManager.migrate_up()
    elif command == 'down':
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        MigrationManager.migrate_down(steps)
    elif command == 'status':
        MigrationManager.status()
    elif command == 'init':
        print("Initializing migrations...")
        with app.app_context():
            db.create_all()
        MigrationManager.get_migration_history()  # Initialize file
        print("✓ Migrations initialized")
    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
