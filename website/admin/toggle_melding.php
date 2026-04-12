<?php
// admin/toggle_melding.php - Beveiligde melding toggle

date_default_timezone_set('Europe/Brussels');

$melding_file = "/home/wwwdata/melding.uit";

// Toggle de status
if (file_exists($melding_file)) {
    unlink($melding_file);
    $status = "uitgeschakeld";
} else {
    touch($melding_file);
    $status = "ingeschakeld";
}

// Automatisch terug naar dashboard
header("Location: ../index.php");
exit;
?>
