import re
import sys
from youtube_transcript_api import YouTubeTranscriptApi

def get_video_id(url):
    """
    Extracts the video ID from a standard YouTube URL.
    """
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if video_id_match:
        return video_id_match.group(1)
    return url # Assume it's already an ID if no match

def format_timestamp(seconds):
    """
    Converts seconds into MM:SS or HH:MM:SS format.
    """
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def download_formatted_transcript(video_url):
    video_id = get_video_id(video_url)
    
    try:
        # Fetch the transcript
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)
        
        formatted_output = ""
        paragraph_start_time = None
        
        for entry in transcript:
            start_time = entry.start
            text = entry.text.replace('\n', ' ') # Clean up newlines in text
            
            # Start a new paragraph
            if paragraph_start_time is None:
                paragraph_start_time = start_time
                timestamp_label = format_timestamp(start_time)
                # YouTube timestamp links use ?t=seconds
                link = f"https://youtu.be/{video_id}?t={int(start_time)}"
                formatted_output += f"[{timestamp_label}]({link}) "
            
            # Check for a break condition if we've passed 10 seconds
            p_duration = start_time - paragraph_start_time
            if p_duration >= 10:
                # Look for the first sentence ender (. ! ?) followed by space or end of string
                match = re.search(r'([.!?])(\s+|$)', text)
                if match:
                    split_idx = match.end()
                    before = text[:split_idx]
                    after = text[split_idx:]
                    
                    formatted_output += before.strip() + "\n\n"
                    
                    if after.strip():
                        # Start new paragraph with the remainder of the snippet
                        paragraph_start_time = start_time
                        timestamp_label = format_timestamp(start_time)
                        link = f"https://youtu.be/{video_id}?t={int(start_time)}"
                        formatted_output += f"[{timestamp_label}]({link}) {after.strip()} "
                    else:
                        paragraph_start_time = None
                    continue
                
                # Hard cap fallback: if no sentence ender is found for 30 seconds, force a break
                if p_duration >= 30:
                    formatted_output += text.strip() + "\n\n"
                    paragraph_start_time = None
                    continue
            
            # Append the text snippet normally
            formatted_output += f"{text} "
            
        return formatted_output

    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
        result = download_formatted_transcript(video_url)
        print(result)
    else:
        print("Usage: python3 transcription.py <youtube_url>")
        print("Example: python3 transcription.py https://www.youtube.com/watch?v=D14LaBUw0Cs")