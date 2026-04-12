<?php

  /*
  header("Content-Type: image/jpeg");
  echo time() . "\n";

  mkdir("/dev/shm/mjpeg");
  
  $preview_delay = 100000;
  
  //for ($x = 0; $x <= 36000; $x++)
  while(1)
  {
    //$e = microtime();
    //$e = str_replace(' ', '-', $e); 
    #echo "$x\n";
    file_put_contents("/dev/shm/mjpeg/cam1a.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1a.jpg", file_get_contents("http://ipcam-wifi-voordeur/snapshot.cgi?user=admin&pwd=Whoo1234"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam1a.busy");
    file_put_contents("/dev/shm/mjpeg/cam1b.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1b.jpg", file_get_contents("http://ipcam-wifi-voordeur/snapshot.cgi?user=admin&pwd=Whoo1234"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam1b.busy");
    file_put_contents("/dev/shm/mjpeg/cam1c.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1c.jpg", file_get_contents("http://ipcam-wifi-voordeur/snapshot.cgi?user=admin&pwd=Whoo1234"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam1c.busy");
    file_put_contents("/dev/shm/mjpeg/cam1d.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1d.jpg", file_get_contents("http://ipcam-wifi-voordeur/snapshot.cgi?user=admin&pwd=Whoo1234"));
    usleep($preview_delay);
    unlink("/dev/shm/mjpeg/cam1d.busy");
  } 
  echo time() . "\n";
  */
  
  ///////////////////////////////////////////////
  header("Content-Type: image/jpeg");
  echo time() . "\n";

  $camUrl = "http://raspberry5/html/cam_pic.php";
  mkdir("/dev/shm/mjpeg");
  
  $preview_delay = 100000;
  $previousMotion = -1;
  $motion = 0;
  $flash = "/media/usb/remote_flash/frontdoor";
  $last_motion_folder = "";
  $last_motion_folder_complete = "";
  $motionCtr = 0;

  //for ($x = 0; $x <= 36000; $x++)
  while(1)
  {
    if (file_exists("/media/usb/remote_flash/frontdoor/motion.log"))
    {
      $motion = 1;
    }
    else
    {
      $motion = 0;
    }

    if ($motion != $previousMotion)
    {
      $previousMotion = $motion;
      if ($motion == 1)
      {
        $dt = date("Ymd\THis");
        $last_motion_folder = "$flash/mot_$dt";
        $last_motion_folder_complete = "$flash/motion_$dt";
        mkdir("$last_motion_folder");
      }
      if ($motion == 0)
      {
        $motionCtr = 0;
        if ($last_motion_folder != "") { rename("$last_motion_folder", $last_motion_folder_complete); }
      }
    }

    //$e = microtime();
    //$e = str_replace(' ', '-', $e); 
    #echo "$x\n";
    file_put_contents("/dev/shm/mjpeg/cam1a.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1a.jpg", file_get_contents($camUrl));
    if ($motion == 1) { copy("/dev/shm/mjpeg/cam1a.jpg", $last_motion_folder . "/" . "cam1_" . sprintf("%04d", $motionCtr) . ".jpg"); ++$motionCtr; }
    else { usleep($preview_delay); }
    unlink("/dev/shm/mjpeg/cam1a.busy");
    file_put_contents("/dev/shm/mjpeg/cam1b.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1b.jpg", file_get_contents($camUrl));
    if ($motion == 1) { copy("/dev/shm/mjpeg/cam1b.jpg", $last_motion_folder . "/" . "cam1_" . sprintf("%04d", $motionCtr) . ".jpg"); ++$motionCtr; }
    else { usleep($preview_delay); }
    unlink("/dev/shm/mjpeg/cam1b.busy");
    file_put_contents("/dev/shm/mjpeg/cam1c.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1c.jpg", file_get_contents($camUrl));
    if ($motion == 1) { copy("/dev/shm/mjpeg/cam1c.jpg", $last_motion_folder . "/" . "cam1_" . sprintf("%04d", $motionCtr) . ".jpg"); ++$motionCtr; }
    else { usleep($preview_delay); }
    unlink("/dev/shm/mjpeg/cam1c.busy");
    file_put_contents("/dev/shm/mjpeg/cam1d.busy", "busy");
    file_put_contents("/dev/shm/mjpeg/cam1d.jpg", file_get_contents($camUrl));
    if ($motion == 1) { copy("/dev/shm/mjpeg/cam1d.jpg", $last_motion_folder . "/" . "cam1_" . sprintf("%04d", $motionCtr) . ".jpg"); ++$motionCtr; }
    else { usleep($preview_delay); }
    unlink("/dev/shm/mjpeg/cam1d.busy");
  } 
  echo time() . "\n";
  
  ///////////////////////////////////////////////
  
?>
