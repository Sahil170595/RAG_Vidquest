"""
Video processing services for RAG Vidquest.

Handles video file operations, frame extraction, clip slicing,
and subtitle processing with proper error handling and validation.
"""

import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import webvtt
from datetime import datetime, timedelta
import cv2
import numpy as np
from dataclasses import dataclass

from ..config.settings import config
from ..core.exceptions import VideoProcessingError, ErrorCode
from ..config.logging import LoggerMixin, log_performance


@dataclass
class VideoMetadata:
    """Video file metadata."""
    
    file_path: str
    duration: float
    width: int
    height: int
    fps: float
    codec: str
    bitrate: Optional[int] = None


@dataclass
class SubtitleSegment:
    """Subtitle segment with timing information."""
    
    start_time: str
    end_time: str
    text: str
    start_seconds: float
    end_seconds: float


@dataclass
class FrameInfo:
    """Frame extraction information."""
    
    frame_path: str
    timestamp: str
    timestamp_seconds: float
    frame_number: int


class VideoValidator(LoggerMixin):
    """Validates video files and formats."""
    
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    SUPPORTED_CODECS = {'h264', 'h265', 'vp8', 'vp9'}
    
    def validate_file(self, file_path: str) -> bool:
        """Validate video file format and accessibility."""
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                raise VideoProcessingError(f"Video file not found: {file_path}", ErrorCode.VIDEO_NOT_FOUND)
            
            # Check file extension
            if path.suffix.lower() not in self.SUPPORTED_FORMATS:
                raise VideoProcessingError(
                    f"Unsupported video format: {path.suffix}. Supported formats: {self.SUPPORTED_FORMATS}",
                    ErrorCode.VIDEO_FORMAT_ERROR
                )
            
            # Check file size (basic validation)
            if path.stat().st_size == 0:
                raise VideoProcessingError(f"Video file is empty: {file_path}", ErrorCode.VIDEO_FORMAT_ERROR)
            
            return True
            
        except Exception as e:
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Failed to validate video file: {e}", ErrorCode.VIDEO_FORMAT_ERROR)
    
    def get_video_info(self, file_path: str) -> VideoMetadata:
        """Get video metadata using ffprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise VideoProcessingError(
                    f"ffprobe failed: {result.stderr}",
                    ErrorCode.VIDEO_PROCESSING_ERROR
                )
            
            data = result.stdout
            import json
            info = json.loads(data)
            
            # Extract video stream info
            video_stream = None
            for stream in info['streams']:
                if stream['codec_type'] == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise VideoProcessingError("No video stream found", ErrorCode.VIDEO_FORMAT_ERROR)
            
            return VideoMetadata(
                file_path=file_path,
                duration=float(info['format']['duration']),
                width=int(video_stream['width']),
                height=int(video_stream['height']),
                fps=eval(video_stream['r_frame_rate']),
                codec=video_stream['codec_name'],
                bitrate=int(info['format'].get('bit_rate', 0)) if info['format'].get('bit_rate') else None
            )
            
        except Exception as e:
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Failed to get video info: {e}", ErrorCode.VIDEO_PROCESSING_ERROR)


class SubtitleProcessor(LoggerMixin):
    """Processes subtitle files and extracts segments."""
    
    def __init__(self):
        self.supported_formats = {'.vtt', '.srt', '.ass', '.ssa'}
    
    def parse_subtitle_file(self, subtitle_path: str) -> List[SubtitleSegment]:
        """Parse subtitle file and extract segments."""
        try:
            path = Path(subtitle_path)
            
            if not path.exists():
                raise VideoProcessingError(f"Subtitle file not found: {subtitle_path}", ErrorCode.VIDEO_NOT_FOUND)
            
            if path.suffix.lower() not in self.supported_formats:
                raise VideoProcessingError(
                    f"Unsupported subtitle format: {path.suffix}",
                    ErrorCode.VIDEO_FORMAT_ERROR
                )
            
            segments = []
            
            if path.suffix.lower() == '.vtt':
                segments = self._parse_vtt_file(subtitle_path)
            elif path.suffix.lower() == '.srt':
                segments = self._parse_srt_file(subtitle_path)
            else:
                raise VideoProcessingError(
                    f"Subtitle format {path.suffix} not yet implemented",
                    ErrorCode.VIDEO_FORMAT_ERROR
                )
            
            self.logger.info(f"Parsed {len(segments)} subtitle segments from {subtitle_path}")
            return segments
            
        except Exception as e:
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Failed to parse subtitle file: {e}", ErrorCode.VIDEO_PROCESSING_ERROR)
    
    def _parse_vtt_file(self, file_path: str) -> List[SubtitleSegment]:
        """Parse VTT subtitle file."""
        segments = []
        
        for caption in webvtt.read(file_path):
            start_seconds = self._time_to_seconds(caption.start)
            end_seconds = self._time_to_seconds(caption.end)
            
            segments.append(SubtitleSegment(
                start_time=caption.start,
                end_time=caption.end,
                text=caption.text.strip(),
                start_seconds=start_seconds,
                end_seconds=end_seconds
            ))
        
        return segments
    
    def _parse_srt_file(self, file_path: str) -> List[SubtitleSegment]:
        """Parse SRT subtitle file."""
        segments = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple SRT parser (can be enhanced)
        blocks = content.split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # Parse timing line
                timing_line = lines[1]
                if ' --> ' in timing_line:
                    start_time, end_time = timing_line.split(' --> ')
                    text = '\n'.join(lines[2:])
                    
                    start_seconds = self._srt_time_to_seconds(start_time.strip())
                    end_seconds = self._srt_time_to_seconds(end_time.strip())
                    
                    segments.append(SubtitleSegment(
                        start_time=start_time.strip(),
                        end_time=end_time.strip(),
                        text=text.strip(),
                        start_seconds=start_seconds,
                        end_seconds=end_seconds
                    ))
        
        return segments
    
    def _time_to_seconds(self, time_str: str) -> float:
        """Convert time string to seconds."""
        try:
            # Handle VTT format: HH:MM:SS.mmm
            if '.' in time_str:
                time_part, ms_part = time_str.split('.')
                ms = float(f"0.{ms_part}")
            else:
                time_part = time_str
                ms = 0
            
            # Parse HH:MM:SS
            parts = time_part.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds + ms
            elif len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds + ms
            else:
                return float(parts[0]) + ms
                
        except Exception:
            return 0.0
    
    def _srt_time_to_seconds(self, time_str: str) -> float:
        """Convert SRT time format to seconds."""
        try:
            # SRT format: HH:MM:SS,mmm
            time_part, ms_part = time_str.split(',')
            ms = float(f"0.{ms_part}")
            
            parts = time_part.split(':')
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds + ms
            
        except Exception:
            return 0.0


class FrameExtractor(LoggerMixin):
    """Extracts frames from video files."""
    
    def __init__(self):
        self.output_dir = Path(config.paths.frame_output)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @log_performance
    async def extract_frame_at_timestamp(
        self,
        video_path: str,
        timestamp: str,
        output_path: Optional[str] = None
    ) -> FrameInfo:
        """Extract frame at specific timestamp."""
        try:
            if not output_path:
                video_name = Path(video_path).stem
                timestamp_clean = timestamp.replace(':', '-').replace('.', '-')
                output_path = self.output_dir / f"{video_name}_{timestamp_clean}.jpg"
            
            # Convert timestamp to seconds for validation
            timestamp_seconds = self._time_to_seconds(timestamp)
            
            # Use ffmpeg to extract frame
            cmd = [
                'ffmpeg',
                '-ss', timestamp,
                '-i', video_path,
                '-frames:v', '1',
                '-q:v', '2',
                '-y', str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise VideoProcessingError(
                    f"Frame extraction failed: {result.stderr}",
                    ErrorCode.FRAME_EXTRACTION_ERROR
                )
            
            return FrameInfo(
                frame_path=str(output_path),
                timestamp=timestamp,
                timestamp_seconds=timestamp_seconds,
                frame_number=0  # Single frame extraction
            )
            
        except Exception as e:
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Failed to extract frame: {e}", ErrorCode.FRAME_EXTRACTION_ERROR)
    
    def _time_to_seconds(self, time_str: str) -> float:
        """Convert time string to seconds."""
        try:
            if '.' in time_str:
                time_part, ms_part = time_str.split('.')
                ms = float(f"0.{ms_part}")
            else:
                time_part = time_str
                ms = 0
            
            parts = time_part.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds + ms
            elif len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds + ms
            else:
                return float(parts[0]) + ms
                
        except Exception:
            return 0.0


class VideoClipper(LoggerMixin):
    """Creates video clips from source videos."""
    
    def __init__(self):
        self.output_dir = Path(config.paths.clip_output)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @log_performance
    async def create_clip(
        self,
        video_path: str,
        start_time: str,
        end_time: str,
        output_path: Optional[str] = None
    ) -> str:
        """Create video clip from start to end time."""
        try:
            if not output_path:
                video_name = Path(video_path).stem
                start_clean = start_time.replace(':', '-').replace('.', '-')
                end_clean = end_time.replace(':', '-').replace('.', '-')
                output_path = self.output_dir / f"{video_name}_{start_clean}_to_{end_clean}.mp4"
            
            # Use ffmpeg to create clip
            cmd = [
                'ffmpeg',
                '-ss', start_time,
                '-to', end_time,
                '-i', video_path,
                '-c:v', 'copy',
                '-c:a', 'copy',
                '-avoid_negative_ts', 'make_zero',
                '-y', str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise VideoProcessingError(
                    f"Video clipping failed: {result.stderr}",
                    ErrorCode.VIDEO_PROCESSING_ERROR
                )
            
            self.logger.info(f"Created video clip: {output_path}")
            return str(output_path)
            
        except Exception as e:
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Failed to create video clip: {e}", ErrorCode.VIDEO_PROCESSING_ERROR)


class VideoService(LoggerMixin):
    """Main video processing service."""
    
    def __init__(self):
        self.validator = VideoValidator()
        self.subtitle_processor = SubtitleProcessor()
        self.frame_extractor = FrameExtractor()
        self.clipper = VideoClipper()
    
    async def find_video_file(self, video_key: str) -> Optional[str]:
        """Find video file by key in the configured directory."""
        try:
            video_root = Path(config.paths.video_root)
            
            for video_file in video_root.rglob(f"{video_key}.mp4"):
                if video_file.exists():
                    return str(video_file)
            
            # Also check other supported formats
            for ext in ['.avi', '.mov', '.mkv', '.webm']:
                for video_file in video_root.rglob(f"{video_key}{ext}"):
                    if video_file.exists():
                        return str(video_file)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding video file {video_key}: {e}")
            return None
    
    async def get_video_metadata(self, video_path: str) -> VideoMetadata:
        """Get video metadata."""
        self.validator.validate_file(video_path)
        return self.validator.get_video_info(video_path)
    
    async def process_subtitles(self, subtitle_path: str) -> List[SubtitleSegment]:
        """Process subtitle file."""
        return self.subtitle_processor.parse_subtitle_file(subtitle_path)
    
    async def extract_frame(self, video_path: str, timestamp: str) -> FrameInfo:
        """Extract frame from video."""
        return await self.frame_extractor.extract_frame_at_timestamp(video_path, timestamp)
    
    async def create_clip(self, video_path: str, start_time: str, end_time: str) -> str:
        """Create video clip."""
        return await self.clipper.create_clip(video_path, start_time, end_time)


# Global video service instance
video_service = VideoService()
