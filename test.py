import threading

def a(i):
    print(i)

    
for i in range(5):
    t = threading.Thread(target=a,args=(i,))
    t.start()
    
    
    
    
    
    
    
    
    
    
    
    
    
    