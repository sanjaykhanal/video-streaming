# if primary_streaming_url and secondary_streaming_url are set, other parameters are ignored.
# Even local file path like '/home/tests/test.mp4' can be set for testing.

camera_list = [
    {
        "id": 1,
        "protocol": "rtsp",
        "username": "admin",
        "password": "admin@123",
        "ip": "192.168.1.64",
        "port": "554",
        "primary_channel_uri": "Streaming/channels/101",
        "secondary_channel_uri": "Streaming/channels/102",
        "primary_streaming_url": "rtsp://192.168.1.64:554/Streaming/channels/101",
        "secondary_streaming_url": "rtsp://192.168.1.64:554/Streaming/channels/102",
    },
    {
        "id": 2,
        "protocol": "rtsp",
        "username": "admin",
        "password": "admin@123",
        "ip": "192.168.1.65",
        "port": "554",
        "primary_channel_uri": "Streaming/channels/101",
        "secondary_channel_uri": "Streaming/channels/102",
        "primary_streaming_url": "rtsp://192.168.1.65:554/Streaming/channels/101",
        "secondary_streaming_url": "rtsp://192.168.1.65:554/Streaming/channels/102",
    }
]
