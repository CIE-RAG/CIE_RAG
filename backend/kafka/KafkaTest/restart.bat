
docker-compose down
docker rm -f $(docker ps -aq) 2>/dev/null
docker rmi $(docker images | grep -E 'producer|consumer|kafka|zookeeper' | awk '{print $3}') 2>/dev/null
docker system prune -a --volumes -f
docker-compose build --no-cache
docker-compose up -d
echo "Waiting for Kafka to initialize..."
sleep 30
docker-compose ps