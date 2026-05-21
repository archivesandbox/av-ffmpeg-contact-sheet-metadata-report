Purpose:
Research depends on being able to assess assets quickly to determine their value. Contact sheets for video files could help researchers or reference staff quickly make an assessment about whether they should invest the time to watching the entire video.

Installation of FFMPEG on Windows OS:

Add ffmpeg to your PATH
	1. Press Win + S and search for "Environment Variables" → click Edit the system environment variables
	2. Click Environment Variables…
	3. Under System variables, find and select Path → click Edit
	4. Click New and add: C:\ffmpeg\bin
	5. Click OK on all dialogs

Verify the install: Open a new Command Prompt or PowerShell and run:
ffmpeg -version

FFMPEG Resources
Create a contact sheet with timestamps from a video with ffmpeg

https://github.com/BtbN/FFmpeg-Builds/releases

Vish was installed and tried, but it does not add true timecode, so a python script was created to do so


Process - for Windows OS:
	• Open the command prompt
	• Call the Python Script with the following command and add the location path of the files and the destination path of the contact sheets:
	Example:
	py C:\Users\asherin\Documents\video-thumbnails\contact-sheets-ffmpeg.py "C:\Users\asherin\Documents\testclip" "C:\Users\asherin\Documents\testclip"
	
	py C:\Users\asherin\Documents\video-thumbnails\contact-sheet-mdcsv-ffmpeg.py "C:\Users\asherin\Documents\testclip" "C:\Users\asherin\Documents\testclip"
	
	Just a contact sheet:
	contact-sheets-ffmpeg.py
	
	Contact sheet and metadata csv:
	Contact-sheet-mdcsv-ffmpeg.py
	
	It should function for most video formats and can be adapted for others
	Be advised that longer videos will take longer to process
