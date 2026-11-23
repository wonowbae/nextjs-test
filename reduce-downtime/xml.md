3. WinSW XML부터 변경
현재 npm start를 사용하고 있다면 WinSW 설정도 바꿔야 해.
```
<service>
  <id>frontend</id>
  <name>Frontend</name>

  <executable>C:\Program Files\nodejs\node.exe</executable>
  <arguments>server.js</arguments>

  <workingdirectory>C:\services\frontend\releases\101</workingdirectory>

  <env name="PORT" value="3000"/>
  <env name="HOSTNAME" value="127.0.0.1"/>

  <logpath>C:\services\frontend\logs</logpath>
  <log mode="roll"/>
</service>
```

여기서 중요한 부분은 다음 두 개야.
```
<arguments>server.js</arguments>
<workingdirectory>C:\services\frontend\releases\101</workingdirectory>
```

앞으로 Jenkins는 workingdirectory만 새 릴리스 경로로 변경하면 돼. WinSW는 지정된 작업 디렉터리에서 실행 파일을 시작할 수 있어. 
Windows Service Wrapper


처음에는 릴리스 101을 수동 배포해 정상 동작을 확인한 뒤 자동 배포로 전환하는 걸 추천해.
