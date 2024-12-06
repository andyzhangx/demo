## debug `os.ReadLink` function on Windows node
### set up test.go and go.mod files
 - test.go
```
package main

import (
    "fmt"
    "os"
)

func main() {
    // get the input path from the command-line arguments
    if len(os.Args) < 2 {
        fmt.Println("Usage: go run main.go <input_path>")
        return
    }
    inputPath := os.Args[1]

    // read the symlink target
    targetPath, err := os.Readlink(inputPath)
    if err != nil {
        fmt.Println("Error reading symlink:", err)
        return
    }

    // print the target path
    fmt.Println("Symlink target:", targetPath)
}
```
 - go.mod
```
module test

go 1.23

godebug winreadlinkvolume=0

godebug winsymlink=0
```


### build windows binary `osreadlink.exe`
```
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -o osreadlink.exe
```

### kubectl cp `osreadlink.exe` to Windows node under C:\ dir
```
kubectl cp osreadlink3.exe kube-system/csi-azuredisk-node-win-m2gn5:osreadlink.exe -c azuredisk
```

