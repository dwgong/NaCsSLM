import zmq

class Client(object):
    def recreate_sock(self):
        if self.__sock is not None:
            self.__sock.close()
        self.__sock = self.__ctx.socket(zmq.REQ)
        self.__sock.connect(self.__url)

    def __init__(self, url: str):
        # network
        self.__url = url
        self.__ctx = zmq.Context()
        self.__sock = None
        self.recreate_sock()
        self.timeout = 500

    # decorators for polling

    # recv_type = 1 is a string receive
    def poll_recv(recv_type = [1], timeout=1000, flag=0):
        def deco(func):
            def f(self, *args): #timeout in milliseconds
                try:
                    func(self, *args)
                except:
                    pass
                rep = []
                for i in recv_type:
                    if self.__sock.poll(timeout) == 0:
                        rep.append(None)
                    else:
                        if i == 0:
                            rep.append(self.__sock.recv(flag))
                        else:
                            rep.append(self.__sock.recv_string(flag))
                return rep
            return f
        return deco

    @poll_recv([1])
    def send_pattern(self, path_str):
        self.__sock.send_string("use_pattern", zmq.SNDMORE)
        self.__sock.send_string(path_str)
    
    @poll_recv([1], timeout=-1)
    def send_calculate(self, targets, amps, iterations):
        self.__sock.send_string("calculate", zmq.SNDMORE)
        self.__sock.send(targets.tobytes(), zmq.SNDMORE)
        #self.__sock.send(targets.tobytes(), zmq.SNDMORE)
        self.__sock.send(amps.tobytes(), zmq.SNDMORE)
        self.__sock.send(int(iterations).to_bytes(1, 'little'))

    @poll_recv([1, 1], timeout=-1)
    def send_save(self, save_path, save_name):
        self.__sock.send_string("save_calculation", zmq.SNDMORE)
        self.__sock.send_string(save_path, zmq.SNDMORE)
        self.__sock.send_string(save_name)

    @poll_recv([1])
    def send_fresnel_lens(self, focal_length):
        # focal length should be one element array
        self.__sock.send_string("add_fresnel_lens", zmq.SNDMORE)
        self.__sock.send(focal_length.tobytes())

    @poll_recv([1])
    def send_zernike_poly(self, zernike_arr):
        self.__sock.send_string("add_zernike_poly", zmq.SNDMORE)
        self.__sock.send(zernike_arr.tobytes())

    @poll_recv([1])
    def send_reset_add_phase(self):
        self.__sock.send_string("reset_additional_phase")