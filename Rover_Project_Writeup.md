**The goals / steps of this project are the following:**  

**Training / Calibration**  

* Download the simulator and take data in "Training Mode"
* Test out the functions in the Jupyter Notebook provided
* Add functions to detect obstacles and samples of interest (golden rocks)
* Fill in the `process_image()` function with the appropriate image processing steps (perspective transform, color threshold etc.) to get from raw images to a map.  The `output_image` you create in this step should demonstrate that your mapping pipeline works.
* Use `moviepy` to process the images in your saved dataset with the `process_image()` function.  Include the video you produce as part of your submission.

**Autonomous Navigation / Mapping**

* Fill in the `perception_step()` function within the `perception.py` script with the appropriate image processing functions to create a map and update `Rover()` data (similar to what you did with `process_image()` in the notebook). 
* Fill in the `decision_step()` function within the `decision.py` script with conditional statements that take into consideration the outputs of the `perception_step()` in deciding how to issue throttle, brake and steering commands. 
* Iterate on your perception and decision function until your rover does a reasonable (need to define metric) job of navigating and mapping.  

[//]: # (Image References)

[image1]: ./calibration_images/example_grid1.jpg
[image2]: ./calibration_images/example_rock1.jpg 
[image3]: ./misc/perspective.png

## [Rubric](https://review.udacity.com/#!/rubrics/916/view) Points
### Here I will consider the rubric points individually and describe how I addressed each point in my implementation.  

---
### Writeup / README

#### 1. Provide a Writeup / README that includes all the rubric points and how you addressed each one.  You can submit your writeup as markdown or pdf.  

You're reading it!

### Notebook Analysis
#### 1. Run the functions provided in the notebook on test images (first with the test data provided, next on data you have recorded). Add/modify functions to allow for color selection of obstacles and rock samples.
Within the online lab notebook, the functions provided were run using the test data provided. Note that the updated instructions in the online lab note
seem to note that recording my own data is not necessary, so I did not complete that step.

The first major step in the notebook is to work with calibration data. Two images are provided - one with a grid overlay to facilitate later scaling
and transformation functions and a second image of a rock sample to be used to determine appropriate color values for later "perception" of a rock
in the rover camera image.

![alt text][image1] ![alt text][image2]

Using the grid image, two important details can be discovered. First, it will ultimately be necessary to transform a "forward-looking" camera image
(eg the grid image) into a top-down view so it can be added to a world map. To do this transform (details of which will be documented later), it's
important to define a "box" within the calibration image that has a known size so that the top-down image can be transformed and maintain the same
scale as the source image. The grid itself is a 1m x 1m square (this fact is provided in the lesson material). By identifying the x,y coordinates
of each corner of the grid image, a calibration bounding box can be established and used for the top-down transform. Additionally, the grid image
provides a good example of navigable terrain (lighter color simulating sand) and obstacles/non-navigable terrain (mountain walls, etc). Using
this image, RGB values can be derived for a threshold color (in this case, those values are the tuple (160,160,160)). Using this threshold value,
an image from the rover camera can be converted to a black and white image by applying a filter. Any pixel whose RGB value is above the threshold
will be recorded as a black pixel in the resulting image and anything below the threshold becomes a white pixel.

The rock sample image can be used to determine an upper and lower bound of RGB values. Once those values are known, a rover camera image can be
examined programmatically to locate pixels that fall between the upper and lower bound. The algorithmic concept that will be used is that if a 
pixel falls between the lower and upper bound, it's deemed to be a rock since the sample has such a distinct color. The lesson suggested a
conversion to a different color model (HSV), but I found it both easy and accurate to stay within the RGB space and properly define this upper
and lower bound. The RGB values I selected and the code I wrote was able to successfully identify all 6 rocks on virtually every run.

#### 1. Populate the `process_image()` function with the appropriate analysis steps to map pixels identifying navigable terrain, obstacles and rock samples into a worldmap.  Run `process_image()` on your test data using the `moviepy` functions provided to create video output of your result. 

The core code for the notebook is contained in the process_image() function. At a high level, here is the process that the code goes through:

1.  First define a source and destination "box" for the transforms needed to convert from the forward-looking view of the rover camera to a top-down
    view that will be mapped in the world view. The source box is defined in the code using the x,y coordinates of the 4 corners of the grid in the
    grid calibration image shown above. A destination box is defined based on the size of the rover camera image with a scale factor applied.
2.  Using these two rectangles, the perspect_transform() function is called. This function takes as parameters the camera image, the source bounding
    box and the destination bounding box. It then uses the getPerspectiveTransform() function out of the CV2 library to perform the transform of
    the image from forward-looking to top down. As an example, compare the following transformed image to the original grid calibration image to
    understand how this transform works:
    
    ![alt text][image3]

3.  Next, process_image() then uses this transformed image to perform the perception steps necessary (determine navigable terrain, determine
    if there are any rock samples present, and determine non-navigable terrain/obstacles).
    Using the transformed image, the code first calls the above_color_thresh function to determine navigable and non-navigable pixels. The
    image that is returned will be a black and white version of the perspective transform where white pixels represent navigable space (these
    are pixels that fall below the treshold value) and black pixels represent non-navigable terrain (including obstacles). The RGB value
    of (160,160,160) was used as the threshold value as provided by the lesson material. Note that I experimented with slight variations of
    these values with no meaningful improvement in the accuracy of the resultant map.
    The code then calls below_color_thresh to specifically identify obstacles, which are typically slightly darker than the surrounding
    terrain walls. The RGB values used for this ended up being (100,100,100). The resulting image that comes back works similar to the 
    navigable pixel calculation but essentially in reverse - pixels below the threshold will be white and those above will be black.
    Finally, the code calls between_color_thresh using the perspective transformed image to locate rock sample pixels. If there are pixels
    in the source image that are between the RGB values in the function call (in this case, the lower bound worked out to be (140,155,50)
    and the upper bound is (190,190,130); these values were determined using a color picker tool standard on MacOS and additional
    experimentation to hone the values). In this function call, the returned image will have white pixels where a pixel in the source image
    fell between the two RGB values. Those pixels will translate to the world map as a rock sample.
 4. Next a number of steps are taken that ultimately result in updates to the rover's "world map." In the world map, the three color channels
    are used separately to hold, respectively, the navigable terrain map, the obstacle map, and the rock sample map. To achieve this mapping,
    a conversion is needed to go from "rover coordinates" to "world map coordinates." Additionally, the image needs to be rotated to properly
    align with the world map (at any given point in time, the rover will be facing an arbitrary direction with respect to the world map; thus,
    the pixels in the image from the rover camera need to be rotated back to "true north" before they are added to the world map). This 
    process has several sub-steps consisting of first converting each image to rover coordinates (by calling rover_coords), then converting
    that result to polar coordinates (by calling to_polar_coordinates) and then also determining the mean angle of the white space in the image
    (this last step is actually part of the process of deciding what direction to travel in but is handled with the other steps for convenience).
5.  With the perspective-transformed, color-thresholded images now properly processed for addition to the world map, the process_image code then
    adds each of these three images to the respect R, G, or B channels of the world map.
6.  Finally, process_image creates several images as output to be displayed in the RoverSim simulator during the autonomous mode run.
7.  This entire process is repeated every time a new image comes in from the rover camera. As a result of this stream of images over time and the
    motion of the rover itself, the terrain can be mapped effectively assuming that the perception steps are accurately calculated AND the
    code for steering the rover results in proper navigation of the terrain.

### Autonomous Navigation and Mapping

#### 1. Fill in the `perception_step()` (at the bottom of the `perception.py` script) and `decision_step()` (in `decision.py`) functions in the autonomous mapping scripts and an explanation is provided in the writeup of how and why these functions were modified as they were.

In the actual code (not the online lab), the perception_step code follows the same basic flow as the online lab described above. Some additional steps
are taken, however, to improve the accuracy of the resulting map.

Overall, the same sequence as described above for process_image() is followed just as described (and hence will not be repeated here). However,
the following additional code has been added starting relatively "within" step 5 above (there are enhancements to the way step 5 operates as 
described below).

a.  Examine the transformed, thresholded rock image to determine if any rock samples were actually located. In this step, there is a call to
    rock.any(). This function examines the rock image for any white pixels which would represent the presence of a rock sample in the image.
    If any white pixels (representing rock pixels) are found, a calculation is performed to locate the 'nearest' of those pixels. This is done
    to make the mapping of rock samples more accurate. When an image containing a rock sample has been processed, the rock sample pixels will
    actually appear as a 'smear' in the final image. This is a by-product of the perspective transform function. The nearest pixels represent
    the actual location of the rock, so that's why that location is used. Then that pixel is set and the rock map is updated. Note that to
    enhance the accuracy of the world rock map, if there were no rock samples located, the image is set to all black. 
b.  Next, in order to improve the accuracy of the navigable terrain, the rover telemetry is examined to identify if the rover is presently in
    a state other than basically flat. If the rover is tilted (think in terms of flat ground as it relates to "tilted"), the resulting camera
    image is actually skewed relative to "reality" (it too will be tilted). If this image is mapped as-is, there will be error introduced to 
    the final map due to this skew. This in mind, the roll (which represents "side to side" tilt of the rover) and the pitch (which represents
    "front to back" tilt of the rover) are both examined. In each case, "threshold" values were determined through trial and error (see the
    code for what those values ended up being). If either the pitch or the roll are "out of bounds," the world map is NOT updated with the
    navigable pixels. This reduces error in the final map.
    
Once the above adjustments are made, the respective world map channels will have been updated properly.

#### 2. Launching in autonomous mode your rover can navigate and map autonomously.  Explain your results and how you might improve them in your writeup.  

**Note: running the simulator with different choices of resolution and graphics quality may produce different results, particularly on different machines!  Make a note of your simulator settings (resolution and graphics quality set on launch) and frames per second (FPS output to terminal by `drive_rover.py`) in your writeup when you submit the project so your reviewer can reproduce your results.**

In my run of the code in autonomous mode, I chose to run the simulator at a resolution of 1024 x 768. This produced frame rates approaching 60 FPS.
To review the simulator run, please see the file 'Autonomous_Run.mp4' in the output folder of this project.

As you review the recorded simulator run, you'll notice that the project goals for accuracy of at least 60% and mapping of at least 30% of the
terrain are easily achieved. Note also the successful locates of rock samples.

The major improvement that could be made to the code is to revise the steering approach. As it is now, it's possible for the rover to get stuck
circling over and over again in a particularly large open are of the terrain. I did not attempt to solve this due to time constraints. The
other improvement that could be made is to actually stop and pick up the rock samples. Again, no attempt to complete that was made due to time
constraints. Neither of those improvements are required for this project.



