<?php

  header("Content-Type: image/jpeg");
  echo time() . "\n";

  mkdir("/dev/shm/mjpeg");
  chmod("/dev/shm/mjpeg", 0777);
  $camUrl = "http://raspberry11/cam/cam_pic.php";
  //$camUrl = "http://192.168.123.143/cgi-bin/api.cgi?cmd=Snap&channel=0&user=admin&password=Whoo1124&width=640&height=480";
  $preview_delay = 20000;

  $fileGiottiDash = '/dev/shm/mjpeg/cam4_rotation_counter.txt';
  $maxAgeFileGiottiDash = 5; // seconden


  while(1)
  {
    // Gebruik clearstatcache() als je dit script in een loop draait
    clearstatcache(true, $fileGiottiDash);

    if (file_exists($fileGiottiDash) && (time() - filemtime($fileGiottiDash)) <= $maxAgeFileGiottiDash)
    {
      chmod("/dev/shm/mjpeg/cam4a.jpg", 0777);
      chmod("/dev/shm/mjpeg/cam4b.jpg", 0777);
      chmod("/dev/shm/mjpeg/cam4c.jpg", 0777);
      chmod("/dev/shm/mjpeg/cam4d.jpg", 0777);
      continue;
    }
    //$e = microtime();
    //$e = str_replace(' ', '-', $e);
    #echo "$x\n";
    file_put_contents("/dev/shm/mjpeg/cam4a.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam4a.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam4a.busy");
    file_put_contents("/dev/shm/mjpeg/cam4b.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam4b.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam4b.busy");
    file_put_contents("/dev/shm/mjpeg/cam4c.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam4c.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam4c.busy");
    file_put_contents("/dev/shm/mjpeg/cam4d.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam4d.jpg", file_get_contents($camUrl));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam4d.busy");
  }

  // Deprecated.
  while(1)
  {
    //$e = microtime();
    //$e = str_replace(' ', '-', $e);
    #echo "$x\n";
    file_put_contents("/dev/shm/mjpeg/cam4a.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam4a.jpg", file_get_contents("http://raspberry18/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam4a.busy");
    file_put_contents("/dev/shm/mjpeg/cam4b.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam4b.jpg", file_get_contents("http://raspberry18/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam4b.busy");
    file_put_contents("/dev/shm/mjpeg/cam4c.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam4c.jpg", file_get_contents("http://raspberry18/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam4c.busy");
    file_put_contents("/dev/shm/mjpeg/cam4d.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam4d.jpg", file_get_contents("http://raspberry18/html/cam_pic.php"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam4d.busy");
  }
  echo time() . "\n";
?>
