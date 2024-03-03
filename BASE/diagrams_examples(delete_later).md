<div class="mermaid">
graph RL
    A[Hard edge] -->|Link text| B(Round edge)
    B --> C{Decision}
    C -->|One| D[Result one]
    C -->|Two| E[Result two]
</div>

```mermaid
graph LR
    A[Hard edge] -->|Link text| B(Round edge)
    B --> C{Decision}
    C -->|One| D[Result one]
    C -->|Two| E[Result two]
```




```mermaid
graph TD;
  A-->B;
  A-->C;
  B-->D;
  C-->D;
```


```mermaid
graph LR;
    A-->B;
    B-->C;
    C-->D;
```    
    
<div class="mermaid">    
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>Bob: Hello Bob, how are you?
    Bob-->>Alice: I'm good, thanks! 
</div>

<div class="mermaid">
graph TB;
    A-->B;
    A-->C;
    B-->D;
    C-->D;
</div>
