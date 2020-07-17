https://kubernetes.io/docs/tasks/administer-cluster/cpu-management-policies/#static-policy

```console
grep -qxF 'cpu-manager-policy=static' /etc/default/kubelet || sed -i 's/protect-kernel-defaults=true/protect-kernel-defaults=true --cpu-manager-policy=static --reserved-cpus=1/g' /etc/default/kubelet
systemctl restart kubelet

Jul 17 03:15:25 k8s-master-15204971-0 kubelet[10986]: E0717 03:15:25.994650   10986 container_manager_linux.go:335] failed to initialize cpu manager: [cpumanager] unable to determine reserved CPU resources for static policy


Jul 17 03:27:06 k8s-master-15204971-0 kubelet[23008]: E0717 03:27:06.676922   23008 cpu_manager.go:194] [cpumanager] could not initialize checkpoint manager: could not restore state from checkpoint: configured policy "static" differs from state checkpoint policy "none", please drain this node and delete the CPU manager checkpoint file "/var/lib/kubelet/cpu_manager_state" before restarting Kubelet, please drain node and remove policy state file
Jul 17 03:27:06 k8s-master-15204971-0 kubelet[23008]: F0717 03:27:06.677031   23008 kubelet.go:1306] Failed to start ContainerManager start cpu manager error: could not restore state from checkpoint: configured policy "static" differs from state checkpoint policy "none", please drain this node and delete the CPU manager checkpoint file "/var/lib/kubelet/cpu_manager_state" before restarting Kubelet
```
