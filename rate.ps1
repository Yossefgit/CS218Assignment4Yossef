1..7 | ForEach-Object {
  curl.exe -s -o NUL -w "%{http_code}`n" http://localhost:8080/items/1
}