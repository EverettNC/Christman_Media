import os

class VideoExport:
    def __init__(self, output_dir="data/output"):
        self.output_dir = output_dir

    def finalize(self, file_path):
        """Verifies output and logs the successful export."""
        # If file_path is already a full path, use it. Otherwise, join it.
        output_path = file_path if os.path.exists(file_path) else os.path.join(self.output_dir, file_path)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"SUCCESS: Export finalized at {output_path}")
            print(f"File size: {os.path.getsize(output_path) / 1024:.2f} KB")
            return output_path
        else:
            print(f"CRITICAL: Export failed or file is corrupted at {output_path}")
            return None
