import numpy as np
import cv2

# Identify pixels above the threshold
# Threshold of RGB > 160 does a nice job of identifying ground pixels only
def above_color_thresh(img, rgb_thresh=(160, 160, 160)):
    # Create an array of zeros same xy size as img, but single channel
    color_select = np.zeros_like(img[:,:,0])
    # Require that each pixel be above all three threshold values in RGB
    # above_thresh will now contain a boolean array with "True"
    # where threshold was met
    above_thresh = (img[:,:,0] > rgb_thresh[0]) \
                & (img[:,:,1] > rgb_thresh[1]) \
                & (img[:,:,2] > rgb_thresh[2])
    # Index the array of zeros with the boolean array and set to 1
    color_select[above_thresh] = 1
    # Return the binary image
    return color_select

# Identify pixels below threshold
def below_color_thresh(img, rgb_thresh=(110, 110, 110)):
    # Create an array of zeros same xy size as img, but single channel
    color_select = np.zeros_like(img[:,:,0])
    # Require that each pixel be BELOW all three threshold values in RGB
    # below_thresh will now contain a boolean array with "True"
    # where threshold was met
    below_thresh = (img[:,:,0] < rgb_thresh[0]) \
                   & (img[:,:,1] < rgb_thresh[1]) \
                   & (img[:,:,2] < rgb_thresh[2])
    # Index the array of zeros with the boolean array and set to 1
    color_select[below_thresh] = 1
    # Return the binary image

    return color_select

# Identify pixels between two threshold values
def between_color_thresh(img, lower_rgb_thresh=(130, 120, 30), upper_rgb_thresh=(220,180,90)):
    # Create an array of zeros same xy size as img, but single channel
    color_select = np.zeros_like(img[:,:,0])
    # Require that each pixel be BETWEEN all three lower threshold values in RGB
    # and all three upper threshold values in RGB
    # below_thresh will now contain a boolean array with "True"
    # where both conditions were met (sample was above lower threshold and below upper threshold)

    between_thresh = ((img[:,:,0] > lower_rgb_thresh[0]) == ((img[:,:,0] < upper_rgb_thresh[0]))) \
                     & ((img[:,:,1] > lower_rgb_thresh[1]) == (img[:,:,1] < upper_rgb_thresh[1])) \
                     & ((img[:,:,2] > lower_rgb_thresh[2]) == (img[:,:,2] < upper_rgb_thresh[2]))
    # Index the array of zeros with the boolean array and set to 1
    color_select[between_thresh] = 1

    # Return the binary image
    return color_select

# Define a function to convert from image coords to rover coords
def rover_coords(binary_img):
    # Identify nonzero pixels
    ypos, xpos = binary_img.nonzero()
    # Calculate pixel positions with reference to the rover position being at the 
    # center bottom of the image.  
    x_pixel = -(ypos - binary_img.shape[0]).astype(np.float)
    y_pixel = -(xpos - binary_img.shape[1]/2 ).astype(np.float)
    return x_pixel, y_pixel


# Define a function to convert to radial coords in rover space
def to_polar_coords(x_pixel, y_pixel):
    # Convert (x_pixel, y_pixel) to (distance, angle) 
    # in polar coordinates in rover space
    # Calculate distance to each pixel
    dist = np.sqrt(x_pixel**2 + y_pixel**2)
    # Calculate angle away from vertical for each pixel
    angles = np.arctan2(y_pixel, x_pixel)
    return dist, angles

# Define a function to map rover space pixels to world space
def rotate_pix(xpix, ypix, yaw):
    # Convert yaw to radians
    yaw_rad = yaw * np.pi / 180
    xpix_rotated = (xpix * np.cos(yaw_rad)) - (ypix * np.sin(yaw_rad))
                            
    ypix_rotated = (xpix * np.sin(yaw_rad)) + (ypix * np.cos(yaw_rad))
    # Return the result  
    return xpix_rotated, ypix_rotated

def translate_pix(xpix_rot, ypix_rot, xpos, ypos, scale): 
    # Apply a scaling and a translation
    xpix_translated = (xpix_rot / scale) + xpos
    ypix_translated = (ypix_rot / scale) + ypos
    # Return the result  
    return xpix_translated, ypix_translated


# Define a function to apply rotation and translation (and clipping)
# Once you define the two functions above this function should work
def pix_to_world(xpix, ypix, xpos, ypos, yaw, world_size, scale):
    # Apply rotation
    xpix_rot, ypix_rot = rotate_pix(xpix, ypix, yaw)
    # Apply translation
    xpix_tran, ypix_tran = translate_pix(xpix_rot, ypix_rot, xpos, ypos, scale)
    # Perform rotation, translation and clipping all at once
    x_pix_world = np.clip(np.int_(xpix_tran), 0, world_size - 1)
    y_pix_world = np.clip(np.int_(ypix_tran), 0, world_size - 1)
    # Return the result
    return x_pix_world, y_pix_world

# Define a function to perform a perspective transform
def perspect_transform(img, src, dst):
           
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (img.shape[1], img.shape[0]))# keep same size as input image
    
    return warped


# Apply the above functions in succession and update the Rover state accordingly
def perception_step(Rover):
    # Perform perception steps to update Rover()
    # NOTE: camera image is coming to you in Rover.img
    # 1) Define source and destination points for perspective transform

    # Define calibration box in source (actual) and destination (desired) coordinates
    # These source and destination points are defined to warp the image
    # to a grid where each 10x10 pixel square represents 1 square meter
    # The destination box will be 2*dst_size on each side
    dst_size = 5
    # Set a bottom offset to account for the fact that the bottom of the image
    # is not the position of the rover but a bit in front of it
    bottom_offset = 6
    source = np.float32([[14, 140], [301 ,140],[200, 96], [118, 96]])
    destination = np.float32([[Rover.img.shape[1]/2 - dst_size, Rover.img.shape[0] - bottom_offset],
                              [Rover.img.shape[1]/2 + dst_size, Rover.img.shape[0] - bottom_offset],
                              [Rover.img.shape[1]/2 + dst_size, Rover.img.shape[0] - 2*dst_size - bottom_offset],
                              [Rover.img.shape[1]/2 - dst_size, Rover.img.shape[0] - 2*dst_size - bottom_offset],
                              ])

    # 2) Apply perspective transform
    warped = perspect_transform(Rover.img, source, destination)

    # 3) Apply color threshold to identify navigable terrain/obstacles/rock samples
    navigable = above_color_thresh(warped, (160, 160, 160))
    obstacle = below_color_thresh(warped, (100, 100, 100))
    rock = between_color_thresh(warped, (140, 155, 50), (190, 190, 130))

    # 4) Update Rover.vision_image (this will be displayed on left side of screen)
    # Example: Rover.vision_image[:,:,0] = obstacle color-thresholded binary image
    #          Rover.vision_image[:,:,1] = rock_sample color-thresholded binary image
    #          Rover.vision_image[:,:,2] = navigable terrain color-thresholded binary image
    # For now, do not update vision_image for rock. That will be handled later.
    Rover.vision_image[:, :, 0] = obstacle * 255
    Rover.vision_image[:, :, 2] = navigable * 255

    # 5) Convert map image pixel values to rover-centric coords
    nav_xpix, nav_ypix = rover_coords(navigable)
    obs_xpix, obs_ypix = rover_coords(obstacle)
    rock_xpix, rock_ypix = rover_coords(rock)

    # 6) Convert rover-centric pixel values to world coordinates
    # First set the scale to 2 x the destination size.
    scale = 2 * dst_size

    # Extract coordinates and yaw from telemetry provided
    rover_xpos = Rover.pos[0]
    rover_ypos = Rover.pos[1]
    rover_yaw = Rover.yaw

    # Now use telemetry data to get navigable pixel positions in world coords
    # Handle navigable pixels
    nav_x_world, nav_y_world = pix_to_world(nav_xpix, nav_ypix, rover_xpos,
                                            rover_ypos, rover_yaw,
                                            Rover.worldmap.shape[0], scale)

    # Now convert obstacle pixels
    obs_x_world, obs_y_world = pix_to_world(obs_xpix, obs_ypix, rover_xpos,
                                            rover_ypos, rover_yaw,
                                            Rover.worldmap.shape[0], scale)

    # And finally convert rock pixels
    rock_x_world, rock_y_world = pix_to_world(rock_xpix, rock_ypix, rover_xpos,
                                              rover_ypos, rover_yaw,
                                              Rover.worldmap.shape[0], scale)

    # For rock pixels, the perspective-transformed version of the camera image will
    # have what amounts to a "smear" where the rock was found. Rather than map all
    # of those pixels, which would be wrong, map only the closest pixel (which essentially
    # represents the face of the rock).
    if rock.any(): # Checks the image to see if there are even any rocks in the image
        # Found rocks, so convert to polar coordinates
        rock_dist, rock_angles = to_polar_coords(rock_xpix, rock_ypix)
        # Now get the index of the nearest pixel - this will basically be the face of the rock
        # and the true position of it. These steps ignore the smear that would be seen on the map
        rock_idx = np.argmin(rock_dist)
        rock_xcen = rock_x_world[rock_idx]
        rock_ycen = rock_y_world[rock_idx]
        # Now that we have identified the rock location in the code just above, set the vision_image
        # to show the whole rock map.
        Rover.vision_image[:, :, 1] = rock * 255
    else: # No rocks found so zero out the channel
        Rover.vision_image[:, :, 1] = 0

    # 7) Update Rover worldmap (to be displayed on right side of screen)
        # Example: Rover.worldmap[obstacle_y_world, obstacle_x_world, 0] += 1
        #          Rover.worldmap[rock_y_world, rock_x_world, 1] += 1
        #          Rover.worldmap[navigable_y_world, navigable_x_world, 2] += 1

    # Check roll and pitch and only add to map if these values are very close to zero, otherwise
    # accuracy of the map is compromised
    if (Rover.roll > 359.5 or Rover.roll < .5) and (Rover.pitch > 359.5 or Rover.pitch < .5):
        # if any rock pixels are present, add the xcen,ycen coordinates to the worldmap. By
        # adding only the xcen,ycen coordinates, this effectively maps only the rock location
        # and not the smear.
        if rock.any():
            Rover.worldmap[rock_ycen, rock_xcen, 1] = 255

        # Now add the nav and obstacle pixels to the worldmap
        Rover.worldmap[nav_y_world, nav_x_world, 2] = 255
        Rover.worldmap[obs_y_world, obs_x_world, 0] = 255

        # There will be overlap between obstacle pixels and navigable pixels. Assume that a navigable
        # pixel "over-rides" an obstacle pixel. In that case, set the corresponding obstacle pixel to
        # 0.
        # This next line extracts the navigable pixels by examining the appropriate channel of the
        # worldmap image. nav_pix will contain essentially a copy of that channel containing all
        # the nav pix
        nav_pix = Rover.worldmap[:,:,2] > 0
        # Now use the nav pixels as a "masK" to set to 0 the corresponding pixels in the obstacle channel
        # The following iterates through the nav_pix array, which is an array of x,y coordinates in
        # world view that have nav pixels. If there is a nav pixel present, then set the corresponding
        # pixel in the obstacle map (channel 0) to 0. This is where the obstacle map is being over-ridden
        # with the navigable pixel data
        Rover.worldmap[nav_pix, 0] = 0


    # 8) Convert rover-centric pixel positions to polar coordinates
    nav_dist, nav_angles = to_polar_coords(nav_xpix, nav_ypix)

    # Update Rover pixel distances and angles
    Rover.nav_dists = np.mean(nav_angles)
    Rover.nav_angles = nav_angles

    return Rover