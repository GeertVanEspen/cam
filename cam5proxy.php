<?php

  header("Content-Type: image/jpeg");
  echo time() . "\n";

  mkdir("/dev/shm/mjpeg");
  
  $preview_delay = 30000;
  
  while(1)
  {
    //$e = microtime();
    //$e = str_replace(' ', '-', $e); 
    #echo "$x\n";
    file_put_contents("/dev/shm/mjpeg/cam5a.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam5a.jpg", file_get_contents("http://portablecam/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam5a.busy");
    file_put_contents("/dev/shm/mjpeg/cam5b.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam5b.jpg", file_get_contents("http://portablecam/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam5b.busy");
    file_put_contents("/dev/shm/mjpeg/cam5c.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam5c.jpg", file_get_contents("http://portablecam/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam5c.busy");
    file_put_contents("/dev/shm/mjpeg/cam5d.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam5d.jpg", file_get_contents("http://portablecam/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam5d.busy");
  } 
  echo time() . "\n";
?>
