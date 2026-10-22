CREATE DATABASE IF NOT EXISTS db_academica CHARACTER SET utf8mb4;
USE db_academica;

CREATE TABLE IF NOT EXISTS usuarios_usss007625 (
  idUsuario INT(10) NOT NULL AUTO_INCREMENT,
  usuario   CHAR(35),
  clave     CHAR(35),
  nombre    CHAR(85),
  direccion CHAR(100),
  telefono  CHAR(9),
  PRIMARY KEY (idUsuario)
);

-- Usuario inicial para poder entrar al login (clave: admin123 en md5)
INSERT INTO usuarios_usss7625 (usuario, clave, nombre, direccion, telefono)
VALUES ('admin', MD5('admin123'), 'Administrador', 'Usulután', '7000-0000');
