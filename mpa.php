<?php

  header("Content-Type: image/jpeg");
  echo time() . "\n";

  mkdir("/dev/shm/mjpeg");
  //$camUrl = "http://raspberry11/cam/cam_pic.php";
  $camUrl = "http://10.42.0.182/cgi-bin/api.cgi?cmd=Snap&channel=0&user=admin&password=Whoo1124&width=640&height=480";
  //$camUrl = "http://ap/mjpeg/cam4a.jpg";
  $preview_delay = 20000;
  
  while(1)
  {
    //$e = microtime();
    //$e = str_replace(' ', '-', $e);
    #echo "$x\n";
    file_put_contents("/nfsshare/shm/mjpeg/cam4a.busy", "busy");
    file_put_contents("/nfsshare/shm/mjpeg/cam4a.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/nfsshare/shm/mjpeg/cam4a.busy");
    file_put_contents("/nfsshare/shm/mjpeg/cam4b.busy", "busy");
    file_put_contents("/nfsshare/shm/mjpeg/cam4b.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/nfsshare/shm/mjpeg/cam4b.busy");
    file_put_contents("/nfsshare/shm/mjpeg/cam4c.busy", "busy");
    file_put_contents("/nfsshare/shm/mjpeg/cam4c.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/nfsshare/shm/mjpeg/cam4c.busy");
    file_put_contents("/nfsshare/shm/mjpeg/cam4d.busy", "busy");
    file_put_contents("/nfsshare/shm/mjpeg/cam4d.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/nfsshare/shm/mjpeg/cam4d.busy");
  }

  echo time() . "\n";
?>
