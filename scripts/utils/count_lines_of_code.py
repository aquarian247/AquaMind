import os
import fnmatch

def count_lines_in_file(file_path):
    """Count the number of lines in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return len(file.readlines())
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

def should_exclude_file(file_path, exclude_patterns):
    """Check if a file should be excluded based on patterns."""
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False

def count_lines_of_code(root_dir, extensions, exclude_dirs, exclude_patterns):
    """Count lines of code in files with specified extensions, excluding certain directories and patterns."""
    total_lines = 0
    file_counts = {}
    all_files = []
    
    for ext in extensions:
        file_counts[ext] = {'files': 0, 'lines': 0}
    
    for root, dirs, files in os.walk(root_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, root_dir)
            
            # Skip files matching exclude patterns
            if should_exclude_file(rel_path, exclude_patterns):
                continue
                
            file_ext = os.path.splitext(file)[1].lstrip('.')
            if file_ext in extensions:
                lines = count_lines_in_file(file_path)
                
                # Store file info for detailed reporting
                all_files.append({
                    'path': rel_path,
                    'ext': file_ext,
                    'lines': lines
                })
                
                total_lines += lines
                file_counts[file_ext]['files'] += 1
                file_counts[file_ext]['lines'] += lines
    
    return total_lines, file_counts, all_files

def print_top_files(all_files, n=10):
    """Print the top N files by line count."""
    sorted_files = sorted(all_files, key=lambda x: x['lines'], reverse=True)
    print(f"\nTop {n} largest files:")
    for i, file_info in enumerate(sorted_files[:n], 1):
        print(f"{i}. {file_info['path']} - {file_info['lines']} lines")

def print_directory_stats(all_files):
    """Print statistics by top-level directory."""
    dir_stats = {}
    for file_info in all_files:
        top_dir = file_info['path'].split(os.sep)[0]
        if top_dir not in dir_stats:
            dir_stats[top_dir] = {'files': 0, 'lines': 0}
        dir_stats[top_dir]['files'] += 1
        dir_stats[top_dir]['lines'] += file_info['lines']
    
    print("\nBreakdown by top-level directory:")
    for dir_name, stats in sorted(dir_stats.items(), key=lambda x: x[1]['lines'], reverse=True):
        print(f"{dir_name}: {stats['files']} files, {stats['lines']} lines")

if __name__ == "__main__":
    # Define the root directory of your project
    root_directory = "."  # Current directory
    
    # Define file extensions to count
    extensions_to_count = ['py', 'js', 'vue', 'html', 'css', 'scss', 'md']
    
    # Define directories to exclude
    exclude_directories = [
        'venv', 'node_modules', '__pycache__', '.git', '.pytest_cache', 
        'build', 'dist', '.eggs', '.vscode', '.idea'
    ]
    
    # Define file patterns to exclude
    exclude_patterns = [
        '*.pyc', '*.pyo', '*.pyd', '*.so', '*.dll', '*.exe',
        '**/migrations/*.py', # We'll count migrations separately
        '**/.DS_Store', '**/Thumbs.db',
        '**/.coverage', '**/.coverage.*',
        '**/*.min.js', '**/*.min.css'
    ]
    
    print("Counting lines of code (excluding generated files)...")
    total, counts_by_ext, all_files = count_lines_of_code(
        root_directory, 
        extensions_to_count, 
        exclude_directories,
        exclude_patterns
    )
    
    print(f"\nTotal lines of code (excluding migrations): {total}")
    print("\nBreakdown by file type:")
    for ext, data in sorted(counts_by_ext.items(), key=lambda x: x[1]['lines'], reverse=True):
        if data['files'] > 0:
            print(f"{ext}: {data['files']} files, {data['lines']} lines")
    
    # Count migrations separately
    migration_patterns = ['**/migrations/*.py']
    exclude_patterns_without_migrations = [p for p in exclude_patterns if p not in migration_patterns]
    
    _, _, migration_files = count_lines_of_code(
        root_directory, 
        ['py'],  # Only count Python migration files
        exclude_directories,
        exclude_patterns_without_migrations
    )
    
    migration_files = [f for f in migration_files if '/migrations/' in f['path'].replace('\\', '/')]
    migration_lines = sum(f['lines'] for f in migration_files)
    
    print(f"\nMigration files: {len(migration_files)} files, {migration_lines} lines")
    print(f"Total lines including migrations: {total + migration_lines}")
    
    # Print top files by line count
    print_top_files(all_files)
    
    # Print directory stats
    print_directory_stats(all_files)
