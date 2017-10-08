# kubernetes developing skills
## kubernetes on Windows
### build kubernetes on Windows
### debug kubernetes windows node
#### create a port 3389 for windows node
1. create an external load balancer in the resource group
2. assign a public address for this load balancer
3. add the windows node in backend pool in the load balancer setting
4. set NAT for the windows node in the load balancer setting, use port mapping 3389
5. after a while, you will get a public address
6. use Windows Remote Desktop to connect to this ip-address:3389
