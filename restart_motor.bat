@echo off
REM Script para reiniciar os serviços do motor via Docker Compose

cd /d %~dp0\motor

echo Parando serviços Docker...
docker-compose down

echo Subindo serviços Docker em modo detached...
docker-compose up -d

echo Serviços reiniciados com sucesso!
pause 