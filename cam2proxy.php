<?php

  header("Content-Type: image/jpeg");
  echo time() . "\n";

  $camUrl = "http://raspberry2/html/cam_pic.php";
  #$camUrl = "http://raspberry2:8080/?action=snapshot";

  mkdir("/dev/shm/mjpeg");
  
  $preview_delay = 100000;
  
  //for ($x = 0; $x <= 36000; $x++)
  while(1)
  {
    file_put_contents("/dev/shm/mjpeg/cam2a.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam2a.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam2a.busy");
    file_put_contents("/dev/shm/mjpeg/cam2b.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam2b.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam2b.busy");
    file_put_contents("/dev/shm/mjpeg/cam2c.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam2c.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam2c.busy");
    file_put_contents("/dev/shm/mjpeg/cam2d.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam2d.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam2d.busy");
  } 
  echo time() . "\n";
?>
