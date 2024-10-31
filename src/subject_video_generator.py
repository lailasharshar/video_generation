import json
from eleven_labs_api import ElevenLabsAPI, DEFAULT_AUDIO
import os
import time
from moviepy.editor import VideoFileClip, TextClip, ImageClip, AudioClip, CompositeVideoClip, AudioFileClip, \
    concatenate_audioclips
from utils import format_name
from PIL import Image
from get_scripts import generate_description, do_script_file

Image.ANTIALIAS = Image.Resampling.LANCZOS  # Compatibility fix for the missing attribute


class SubjectVideoGenerator:
    def __init__(self, subject_name, config, asset_dir ='assets'):

        # Configuration on how to build and which videos to build
        self.config = config

        # The voice to use
        if config['voice_id']:
            self.voice_id = config['voice_id']
        else:
            self.voice_id = DEFAULT_AUDIO

        # location of all the assets
        if not os.path.exists(asset_dir):
            print('Creating asset directory')
            os.mkdir(asset_dir)

        # location of this specific asset
        subject_dir_name = format_name(subject_name)
        self.subject = subject_name
        self.subject_dir = f'{asset_dir}/{subject_dir_name}'
        if not os.path.exists(self.subject_dir):
            print(f'{self.subject}: Creating subject directory')
            os.mkdir(self.subject_dir)

        # define image file
        self.image_path = f'{self.subject_dir}/img.png'

        # define script file that defines content of video. If it doesn't exist, create it.
        self.script_path = f'{self.subject_dir}/script.json'
        if not os.path.exists(self.script_path):
            print(f'{self.subject}: Creating script file')
            do_script_file(self.subject, self.script_path, self.config['agent_instruction'], self.config['script_prompt'])

        # Load the script file content
        with open(self.script_path, 'r') as f:
            self.data = json.load(f)

        # define audio directory, create it if it doesn't exist. If the audio dir has no intro.mp3 file, generate all the audio
        self.audio_dir = f'{self.subject_dir}/audio'
        if not os.path.exists(self.audio_dir):
            print(f'{self.subject}: Creating audio directory')
            os.mkdir(self.audio_dir)
        if not os.path.exists(f'{self.audio_dir}/intro.mp3'):
            self.elevenlabs = ElevenLabsAPI()
            print(f'{self.subject}: Create audio')
            self.generate_all_audio()

        # Video settings
        self.width = 1920
        self.height = 1080
        self.fps = 30

    def generate_all_audio(self):
        # Generate intro narration
        intro_file = f'{self.audio_dir}/intro.mp3'
        if not os.path.exists(intro_file):
            print(f'{self.subject}: Generating intro audio for {self.subject}')
            intro_audio = self.elevenlabs.generate_speech(self.data['description_narration'], self.voice_id)
            with open(intro_file, 'wb') as f:
                f.write(intro_audio)

        # Generate detail narrations
        for idx, detail in enumerate(self.data['details']):
            detail_file = f'{self.audio_dir}/detail_{idx}.mp3'
            if not os.path.exists(detail_file):
                print(f'{self.subject}: Generating detail audio for {idx}')
                audio = self.elevenlabs.generate_speech(detail['narration_value'], self.voice_id)
                with open(detail_file, 'wb') as f:
                    f.write(audio)

        # Allow time for files to be written
        time.sleep(1)

    # Generic method to write the video clip to a file
    def write_video(self, final_video, output_path):
        try:
            final_video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                audio_fps=44100  # Explicitly set audio sample rate
            )
        except Exception as e:
            print(f"{self.subject}: Error during video creation: {str(e)}")
            raise

    # Create audio clips from all the audio files and calculate their total length
    def get_audio_clips(self):
        audio_clips = []
        intro_audio_clip = AudioFileClip(f'{self.audio_dir}/intro.mp3')
        audio_clips.append(intro_audio_clip)
        total_length = intro_audio_clip.duration

        # Calculate total duration and collect audio clips
        detail_audio_clips = []
        for i in range(len(self.data['details'])):
            detail_audio_clip = AudioFileClip(f'{self.audio_dir}/detail_{i}.mp3')
            audio_clips.append(detail_audio_clip)
            total_length += detail_audio_clip.duration

        return audio_clips, total_length

    # Does the hard work of combining all the elements
    def create_main_video(self, picture_subtitle, video_name = 'main_video.mp4'):
        filename = f'{self.subject_dir}/{video_name}'

        # Exit if the video file already exists
        if os.path.exists(filename):
            print(f'{self.subject}: Video already exists at {filename}')
            return

        print(f'{self.subject}: Generating video')
        video_clips = []
        audio_clips, total_length = self.get_audio_clips()

        # Create the outro video clip
        outro_video_clip = VideoFileClip('assets/outro.mp4')
        outro_duration = outro_video_clip.duration

        # Set the outro start time and position
        outro_video_clip = (outro_video_clip
                            .set_start(total_length)  # Start after all other content
                            .set_position(('center', 'center')))

        # Add outro duration to total length after setting start time
        total_length += outro_duration

        # Background and static elements that stay throughout the video
        background_image = ImageClip('assets/template.png').set_duration(total_length - outro_duration)  # End before outro
        video_clips.append(background_image)

        # Add, resize and position the subject image
        image = ImageClip(str(self.image_path))
        image_resized = image.resize(width=590, height=590)
        image_clip = image_resized.set_position((1225, 189)).set_duration(total_length - outro_duration)  # End before outro
        video_clips.append(image_clip)

        # Create the title of the video (the subject)
        title_clip = TextClip(
            self.data['title'].title(),
            fontsize=37,
            color='#2B2C30',
            font='Arial-Bold'
        ).set_position((80, 130)).set_duration(total_length - outro_duration)  # End before outro
        video_clips.append(title_clip)

        # Create a position the picture subtitle below the image
        image_title = TextClip(
            txt=f'{picture_subtitle}{self.data["text_below_image"]}',
            fontsize=37,
            color='#2B2C30',
            font='Arial-Bold'
        ).set_position((1225, 795)).set_duration(total_length - outro_duration)  # End before outro
        image_title = image_title.crossfadein(2)
        video_clips.append(image_title)

        # Handle detail text clips with proper timing
        current_start = audio_clips[0].duration  # Start after intro
        x_pos = 80
        y_pos = 200
        y_diff = 90
        text_indent = 40

        for i, detail in enumerate(self.data['details']):
            detail_duration = audio_clips[i + 1].duration
            remaining_duration = (total_length - outro_duration) - current_start  # End before outro

            # Create title
            title = detail['type'].replace('_', ' ').title()
            detail_title_clip = (TextClip(
                txt=title,
                fontsize=27,
                color='#2B2C30',
                font='Arial-Bold'
            ).set_position((x_pos, y_pos))
                                 .set_duration(remaining_duration)
                                 .set_start(current_start)
                                 .crossfadein(0.5))

            # Create detail text with indentation and wrapping
            detail_text_clip = (TextClip(
                txt=detail['text_value'],
                fontsize=22,
                color='#2B2C30',
                font='Arial',
                method='caption',
                align='west',
                size=(900, None)
            )
                                .set_position((x_pos + text_indent, y_pos + 35))
                                .set_duration(remaining_duration)
                                .set_start(current_start)
                                .crossfadein(0.5))

            video_clips.extend([detail_title_clip, detail_text_clip])

            current_start += detail_duration
            y_pos += y_diff

        # Add the outro video clip
        video_clips.append(outro_video_clip)

        # Compose final video
        title_screen = CompositeVideoClip(
            video_clips,
            size=(self.width, self.height)
        ).set_duration(total_length)

        # Get the outro audio
        outro_audio = outro_video_clip.audio if outro_video_clip.audio is not None else AudioClip(lambda t: 0, duration=outro_duration)

        # Combine all audio clips including outro audio
        final_audio = concatenate_audioclips(
            audio_clips +
            [outro_audio]
        )

        final_video = title_screen.set_audio(final_audio)
        self.write_video(final_video, filename)

    def build_video(self):
        # Check to see if an image exists before you continue to create the video
        if not os.path.exists(self.image_path):
            print(f'{self.subject}: You now have to get an image of {self.subject} before you can continue - called {self.image_path}. The prompt should be: \n    {self.data["ai_image_prompt"]}{self.config['generic_image_prompt']}\n\n')
            return
        self.create_main_video(config['image_subtitle'])

    # Retrieve all the narrations from the script.json file so we can combine them to get the narration of the entire video
    def get_narrations(self):
        narrations = []
        narrations.append(self.data['description_narration'])
        for idx, detail in enumerate(self.data['details']):
            narrations.append(detail['narration_value'])
        return narrations

    # Retrieve all the narrations and then use the LLM to generate a description from those narrations and save it to a file
    def write_description(self):
        file_name = f'{self.subject_dir}/description.txt'
        if os.path.exists(file_name):
            return

        narrations = self.get_narrations()
        description = generate_description(narrations, self.config['agent_instruction'])
        with open(file_name, 'w') as f:
            print(f'{self.subject}: Writing description file')
            f.write(description + '\n')

# Iterate over the subjects and for each, create the video assets and content
def do_all_videos(config):
    subjects = config['subjects']
    for subject in subjects:
        try:
            video_gen = SubjectVideoGenerator(subject, config)
            video_gen.write_description()
            video_gen.build_video()
        except Exception as e:
            print(f"{subject}: Error during video creation: {str(e)}\n{e}")

if __name__ == "__main__":
    # Load the config file with all the subject data and configurations
    config = json.load(open('config.json'))
    # Generate the videos from those instructions
    do_all_videos(config)
