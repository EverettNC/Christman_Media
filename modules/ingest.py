import subprocess
import json
import os

class VideoIngest:
    def __init__(self, file_path):
        self.file_path = file_path
        self.metadata = None

    def validate_and_probe(self):
        """Checks if file exists and extracts metadata using ffprobe."""
        if not os.path.exists(self.file_path):
            print(f"Error: File {self.file_path} not found.")
            return False

        try:
            # Using ffprobe to get stream data in JSON format
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", self.file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.metadata = json.loads(result.stdout)
            print(f"Ingested: {os.path.basename(self.file_path)}")
            return True
        except Exception as e:
            print(f"Critical error during ingestion: {e}")
            return False

    def get_stream_info(self):
        if self.metadata:
            # Returns the primary video stream info
            return next((s for s in self.metadata['streams'] if s['codec_type'] == 'video'), None)
        return None

# Example usage:
# ingest = VideoIngest("data/my_video.mp4")
# if ingest.validate_and_probe():
#     print(ingest.get_stream_info())
