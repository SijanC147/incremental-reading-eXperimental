# IR3X (_Incremental Reading 3 eXperimental_) for Anki 2.0 

## Introduction 
This is an experimental version of the original Incremental Reading for Anki add-on in an effort to bring some of the features of v4 of that add-on to Anki 2.0, and some others. It is in no way affiliated with that project other than being built on top of it. All issues and bugs for this add-on should be reported on this repo. 

## Main Features
* Priority system using multiple schedules
* Templating engine for quick-key extracts to control what goes in which field specifically
* Ability to import images from clipboard, with options for compression and captioning
* Special support for images from wikipedia, to avoid downloading low quality thumbnails
* An Image management system for notes, able to extract images and pass them to child extracts
* Persistent note history which is maintained even after closing Anki 
* New automatic-title option for extracted notes
* Added support for bold, italic, underline and strikethrough formatting
* New overlay settings to toggle highlights, removed text and formatting
* Note hyperlinks, let's you open any extracted note for editing, from the parent note itself
* New note layout and styling with an integrated images sidebar to view imported images
* Integrated Issue Reporter

## Instructions 
The add-on includes a _getting started_ note which goes through some of the main features, along with instruction messages that appear while using the add-on.

## Installation
* Extract the `ir3x.py` file and `ir3x` directory from the archive to your Anki 2.0 addons folder.
* Restart anki and follow along with the instruction messages that follow. 

## Usage Examples
Below are some examples of the functionality provided by the add-on

* [Extracting images from a note](https://i.imgur.com/25L9O4e.gif)
* [Toggling different overlays](https://i.imgur.com/JUbM4ax.gif)
* [Moving and editing extracted images](https://i.imgur.com/jlhICSP.gifv)
* [Creating extracts with direct links](https://i.imgur.com/GTdrfFz.gifv)
* [Undo operation with note deletion](https://i.imgur.com/TQv6Lo4.gifv)
* [Adding new schedules](https://i.imgur.com/DIzaxH8.gifv)


## Support
The add-on includes a custom issue reporter which can be used to log any issues you encounter. The main advantage of using the issue reporter is that it auto-formats your issues to conform to a standard template, while also including any error and platform information automatically. The issue reporter will not post anything, it will simply copy the formatted issue to your clipboard and open the issues page on this repo. You are still required to paste in thie information and finally submit the issue. 

## Future Plans 
I will be slowing down future development of the add-on due to other obligations for the time being. The idea is that hopegfully through beta testing I will be able to identify bugs which I can address when I pick it up again. That notwithstanding, the following are some features which I intended on including but could not due to lack of time and resources. These are the top priorities I will be adressing when time permits. 

* Implementing a way to import content from online sources like wikipedia and others. This is my #1 priority, as I understand the lack of this feature limits the add-on substiantially. 
* A more robust image manager that allows moving images between notes, searching and importing new images from within Anki itself. 
* A separate history navigation interface which would allow _redoing_ specific actions apart from the standard _undo_, and previewing/restoring to specific snapshots of a note's history.
* A more sophisticated scheduling system which would take into account how the user is performing in cards originating from the parent, to decide when best to show the parent note to the user again.