from multiprocessing import Process, Queue
from comm import Communication
from vision import Vision

if __name__ == "__main__":
    comm = Communication(ip_address='0.0.0.0') #ip address of the machine connected with the ABB Robot
    vis = Vision(model_path=r'H:/Final_INA_700_Project/best.pt')
    
    vis.set_color_range("Black", [0, 0, 0], [180, 255, 50])
    vis.set_color_range("Blue", [94, 145, 2], [135, 255, 255])
    vis.set_color_range("Green", [45, 160, 40], [90, 255, 83])
    vis.set_color_range("Red", [0, 76, 0], [15, 255, 255])
    
    command_queue = Queue()  # comm → vision
    result_queue = Queue()   # vision → comm

    p1 = Process(target=comm.comm_process, args=(command_queue, result_queue))
    p2 = Process(target=vis.vision_process, args=(command_queue, result_queue))

    p1.start()
    p2.start()
    p1.join()
    p2.join()