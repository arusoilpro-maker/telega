<?php
// Подключение к базе SQLite (или MySQL)
$db = new PDO('sqlite:../database.db');
$stmt = $db->query("SELECT * FROM orders ORDER BY created_at DESC LIMIT 10");
$orders = $stmt->fetchAll(PDO::FETCH_ASSOC);
?>
<h1>Панель управления</h1>
<table>
    <tr><th>ID</th><th>Клиент</th><th>Статус</th><th>Сумма</th></tr>
    <?php foreach ($orders as $order): ?>
    <tr>
        <td><?= $order['id'] ?></td>
        <td><?= $order['client_id'] ?></td>
        <td><?= $order['status'] ?></td>
        <td><?= $order['total_price'] ?></td>
    </tr>
    <?php endforeach; ?>
</table>