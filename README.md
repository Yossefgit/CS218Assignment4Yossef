Assignment 3 Yossef

github link: https://github.com/Yossefgit/CS218Assignment3Yossef

my public ALB URL:
http://cs218-a3-alb-500597902.us-east-1.elb.amazonaws.com

ECS service name:
cs218-a3-service

for secret handling for my local secret handling i used .env and for the network AWS secret handeling i used the AWS SSM store to store the database password

migration are executed using alembic and when the container executes this command the migration is executed - python -m alembic upgrade head

database type used is RDS and the instance type for it is db.t4g.micro

my ECS instance type is 256 CPU 512 MB memory 


local setup steps 
1 get the github file and cd into it
2 start up the docker command is:
docker compose up -d --build
(so at this point it's set up but these are the rest of the commands to make sure the test scenarios pass in the local setup)

test scenarios
before i start i just want to note that the syntax i used for some of the canvas commands were different than the canvas commands but it still completes the same thing.

1 
we check test scenario 1 which is Local Compose Boot + DB-Aware Health Check. command is:
curl http://localhost:8080/health
expected is to get HTTP 200 with DB connected status and we do get that:
![alt text](image.png)
2 
for text scenario 2 which is Persistence Across API Restart so we will basically create a record and it should work at creating it and after restarting the api and read the record back we should get 200 OK and the record still exists
i used this command to create an record:
curl -Method POST "http://localhost:8080/items" -Headers @{"Content-Type"="application/json"} -Body '{"name":"alpha","value":123}'
I got it created sucsessfully
![alt text](image-2.png)
i used this docker command to restart the API:
docker compose restart api
and this to read the record back the id number at the end needs to match the record we are calling which in this case is 305:
curl "http://localhost:8080/items/305"
the same record was read back
![alt text](image-3.png)
3
for Postgres Volume Persistence what is tested is that the record that we made in test scenario 2 is still there and still exists after restarting postgres. I ran
docker compose restart postgres
and than i try to read the record the id number of the end needs to match the record like in test scenario 2 so in this case it's this command again:
curl "http://localhost:8080/items/305"
4
for test scenario 4 which is AWS Health Endpoint via ALB what we should get is HTTP 200 with DB connected status after running the command below 
curl "http://cs218-a3-alb-500597902.us-east-1.elb.amazonaws.com/health"
we do get the expected output
![alt text](image-4.png)
5
for test scenario 5 which is AWS Write + Read Verification I run a POST method and a GET method to retrieve exactly what i just posted and the expected result is that POST returns id and the GET returns that same record
for the POST command this is what I ran:
PS C:\Users\water\CS218Assignment3Yossef> curl -Method POST "http://cs218-a3-alb-500597902.us-east-1.elb.amazonaws.com/items" -Headers @{"Content-Type"="application/json"} -Body '{"name":"cloud-alpha","value":456}'
and this is the result which is expected and the id is important for the GET method and in this case the id is 3
![alt text](image-5.png)
the GET command i ran was:
curl "http://cs218-a3-alb-500597902.us-east-1.elb.amazonaws.com/items/3"
it correctly returns the same record
![alt text](image-6.png)
6
for test scenario 6 which is Local Load Test (k6) I ran:
k6 run loadtest.js
I got multiple things so my image only covers the top
![alt text](image-7.png)
This is a summary of the findings:
there were 584 requests in the 30 seconds of testing
I got 0.00% failed requests so none out of the 584 requests failed
my RPS is 19.072238/s
my average latency is 20.7ms
minimum = 1.07ms
median = 9.6ms
max = 257.21ms
P90 = 34.22ms
P95 = 65.22ms



AWS deployment steps

1 run:
aws configure
and enter in the acc information. for the region i used us-east-1.
2 create ECR repository:
aws ecr create-repository --repository-name cs218-a3-api
3 we now log the docker into the ECR so need to run
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 210190733205.dkr.ecr.us-east-1.amazonaws.com
4 now we need to build and push the docker image so this takes 3 commands that we need to run top to bottom
a
docker build -t cs218assignment3yossef-api .
b
docker tag cs218assignment3yossef-api:latest 210190733205.dkr.ecr.us-east-1.amazonaws.com/cs218-a3-api:latest
c
docker push 210190733205.dkr.ecr.us-east-1.amazonaws.com/cs218-a3-api:latest
5 we create the RDS database in the AWS console website. most things i kept default but the key things are making sure it is:
a PostgreSQL
b the instance type is db.t4g.micro
6 I stored the database password in AWS SSM store 
7 I than created ECS task definition which runs on AWS fargate, and used the image from the ECR and also included the cloudwatch for the logs.
8 I created the ECS service
9 I made the ALB and connected it to the ECS service