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
    file_put_contents("/dev/shm/mjpeg/cam3a.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam3a.jpg", file_get_contents("http://raspberry12/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam3a.busy");
    file_put_contents("/dev/shm/mjpeg/cam3b.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam3b.jpg", file_get_contents("http://raspberry12/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam3b.busy");
    file_put_contents("/dev/shm/mjpeg/cam3c.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam3c.jpg", file_get_contents("http://raspberry12/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam3c.busy");
    file_put_contents("/dev/shm/mjpeg/cam3d.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam3d.jpg", file_get_contents("http://raspberry12/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam3d.busy");
  } 
  echo time() . "\n";
?>
