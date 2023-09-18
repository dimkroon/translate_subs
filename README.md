Translate Subs
==============

This is an experimental Kodi addon intending to provide automatic 
translation of subtitles using various online translation services.

The addon basically re-packs the python package [translatepy](https://github.com/Animenosekai/translate) 
for Kodi and adds a little to:
* perform automatic translation
* offer subtitles text to the translation service in such a way to ensure 
  optimal translation result.
* optionally suppress colourisation of subtitles intended for the hearing 
  impaired.
* optionally suppress sound descriptions in subtitles intended for the 
  hearing impaired.
* optionally suppress lyrics of songs in subtitles intended for the 
  hearing impaired.

Check the addon's settings to enable automatic translation and to set various 
other options.

The latest version of the addon can only perform automatic translation on 
subtitles provided by video add-ons that actively support translation. 
Currently, viwX is the only addon known to do so.

The addon is still at a very rough state. 
Development is primarily focused on translating western European languages, 
English in particular. Please drop a note on 
[Github discussions](https://github.com/dimkroon/translate_subs/discussions) 
if you encounter issues with a particular language, or file an issue at 
[Github](https://github.com/dimkroon/translate_subs/issues)

## Error Marking
From version 0.2.0 errors can be marked while you watch a video. 
If you notice some strange characters, or miss pieces of text while you 
watch a video, press the red button on the remote, or the 'a' key on a 
keyboard. This will copy the relevant info to folder in userdata/service.
subtitles.translate/errors/<date> <time>. The files in the folder can be 
used to inspect the error at a later time.

To enable error marking via keyboard or remote button, you have to map a 
button to a function in the addon. The easiest way to do this is to copy the 
file [*translation_error_marking.xml*](https://github.com/dimkroon/translate_subs/blob/development/translation_error_marking.xml) to 
*userdata/keymaps* on your Kodi system.
Check [https://kodi.wiki/view/Keymap#Location_of_keymaps](https://kodi.wiki/view/Keymap#Location_of_keymaps)
for the exact location of the keymaps folder on various operating systems.
You have to restart Kodi before these changes take effect.

## Support
Head to [https://github.com/dimkroon/translate_subs/discussions](https://github.com/dimkroon/translate_subs/discussions)
for question remarks, ideas, or anything else you want to discuss regarding this
addon.
