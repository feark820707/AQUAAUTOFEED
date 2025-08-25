"""
ROS2啟動文件
用於啟動完整的智能餵料系統
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, TimerAction
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    """生成啟動描述"""
    
    # 獲取包路徑
    package_dir = get_package_share_directory('aqua_feeder')
    config_file = os.path.join(package_dir, 'config', 'system_params.yaml')
    
    # 定義節點
    nodes = []
    
    # 1. 相機節點（使用 usb_cam 包）
    camera_node = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='camera_node',
        parameters=[{
            'video_device': '/dev/video0',
            'image_width': 1920,
            'image_height': 1080,
            'pixel_format': 'yuyv',
            'camera_frame_id': 'camera_link',
            'io_method': 'mmap',
            'framerate': 60.0,
        }],
        remappings=[
            ('image_raw', 'camera/image_raw'),
        ]
    )
    nodes.append(camera_node)
    
    # 2. 視覺處理節點
    vision_node = Node(
        package='aqua_feeder',
        executable='vision_node',
        name='vision_node',
        parameters=[config_file],
        remappings=[
            ('camera/image_raw', 'camera/image_raw'),
            ('aqua_feeder/features', 'aqua_feeder/features'),
            ('aqua_feeder/debug_image', 'aqua_feeder/debug_image'),
        ]
    )
    # 延遲啟動視覺節點，等待相機準備
    vision_node_delayed = TimerAction(
        period=3.0,
        actions=[vision_node]
    )
    nodes.append(vision_node_delayed)
    
    # 3. 控制節點
    control_node = Node(
        package='aqua_feeder',
        executable='control_node',
        name='control_node',
        parameters=[config_file],
        remappings=[
            ('aqua_feeder/features', 'aqua_feeder/features'),
            ('aqua_feeder/pwm_command', 'aqua_feeder/pwm_command'),
            ('aqua_feeder/control_status', 'aqua_feeder/control_status'),
        ]
    )
    # 延遲啟動控制節點
    control_node_delayed = TimerAction(
        period=5.0,
        actions=[control_node]
    )
    nodes.append(control_node_delayed)
    
    # 4. 硬體接口節點
    hardware_node = Node(
        package='aqua_feeder',
        executable='hardware_node',
        name='hardware_node',
        parameters=[config_file],
        remappings=[
            ('aqua_feeder/pwm_command', 'aqua_feeder/pwm_command'),
            ('aqua_feeder/hardware_status', 'aqua_feeder/hardware_status'),
        ]
    )
    # 延遲啟動硬體節點
    hardware_node_delayed = TimerAction(
        period=2.0,
        actions=[hardware_node]
    )
    nodes.append(hardware_node_delayed)
    
    # 5. 系統監控節點（可選）
    monitor_node = Node(
        package='aqua_feeder',
        executable='system_monitor',
        name='system_monitor',
        parameters=[config_file],
        condition='if_arg_equals',
        arguments=['monitor', 'true']
    )
    nodes.append(monitor_node)
    
    # 6. RViz可視化（開發用，可選）
    rviz_config = os.path.join(package_dir, 'config', 'aqua_feeder.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        condition='if_arg_equals',
        arguments=['rviz', 'true']
    )
    nodes.append(rviz_node)
    
    return LaunchDescription(nodes)

# 簡化版啟動（僅核心功能）
def generate_simple_launch_description():
    """生成簡化版啟動描述（僅核心功能）"""
    
    # 主控制器節點
    main_controller = Node(
        package='aqua_feeder',
        executable='main_controller',
        name='aqua_feeder_main',
        output='screen',
        parameters=[{
            'config_file': 'config/system_params.yaml',
            'log_level': 'INFO'
        }]
    )
    
    return LaunchDescription([main_controller])
