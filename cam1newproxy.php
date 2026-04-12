<?php

  header("Content-Type: image/jpeg");
  echo time() . "\n";

  $camUrl = "http://raspberry5a/cam/cam_pic.php";
  mkdir("/dev/shm/mjpeg");
  
  $preview_delay = 100000;
  
  //for ($x = 0; $x <= 36000; $x++)
  while(1)
  {
    //$e = microtime();
    //$e = str_replace(' ', '-', $e); 
    #echo "$x\n";
    file_put_contents("/dev/shm/mjpeg/cam1na.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1na.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam1na.busy");
    file_put_contents("/dev/shm/mjpeg/cam1nb.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1nb.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam1nb.busy");
    file_put_contents("/dev/shm/mjpeg/cam1nc.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1nc.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam1nc.busy");
    file_put_contents("/dev/shm/mjpeg/cam1nd.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1nd.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam1nd.busy");
  } 
  echo time() . "\n";
?>
