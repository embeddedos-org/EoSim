# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""ROS 2 node bridge for EoSim integration.

Transports (explicit — ``connect()`` takes a ``transport`` argument):

- ``"auto"`` (default): try rclpy first, exactly as before. Without
  rclpy installed, ``connect()`` returns ``False`` — unchanged
  behaviour. No silent fallback: code that checks the return value
  keeps meaning what it meant.
- ``"rclpy"``: force real ROS 2. Returns ``False`` when rclpy is
  absent (fails closed, no fallback).
- ``"loopback"``: an opt-in, in-process test/offline transport.
  ``publish()`` delivers the data dict synchronously to every
  subscriber of the topic in this process. This is NOT ROS wire
  compatibility — no ROS tool can speak to it — it exists so CI
  (no ROS installed) can prove topic mapping end to end, and so a
  sim can be driven from a topic contract before any ROS
  installation exists. A real socket/TCP transport is future work,
  not something this module claims today.

On the rclpy path, message types are given as strings such as
``"geometry_msgs/msg/Twist"`` and resolved to classes with importlib
inside the publish/subscribe call, so no ROS message package is
imported at module load time. If the message package is
unimportable, publish/subscribe raise an informative error — they
never send dicts over a real ROS graph and call that ROS 2.

Tracks: https://github.com/embeddedos-org/EoSim/issues/52
"""

import threading

# Process-local topic bus for the loopback transport: topic -> [callback].
# Callbacks receive (topic, msg_type, data). Delivery is synchronous and
# guarded by a lock; a callback raising does not break other subscribers.
_LOOPBACK_LOCK = threading.Lock()
_LOOPBACK_BUS = {}


def _loopback_subscribe(topic, callback):
    with _LOOPBACK_LOCK:
        _LOOPBACK_BUS.setdefault(topic, []).append(callback)


def _loopback_unsubscribe(topic, callback):
    with _LOOPBACK_LOCK:
        callbacks = _LOOPBACK_BUS.get(topic, [])
        if callback in callbacks:
            callbacks.remove(callback)


def _loopback_publish(topic, msg_type, data):
    with _LOOPBACK_LOCK:
        callbacks = list(_LOOPBACK_BUS.get(topic, []))
    for callback in callbacks:
        try:
            callback(topic, msg_type, data)
        except Exception:
            # A subscriber must not take down the publisher.
            continue


def _resolve_msg_class(msg_type):
    """Resolve "package/msg/Name" to a ROS message class via importlib.

    Raises ImportError (package missing) or ValueError (bad shape) with
    a message that names the requested type.
    """
    parts = msg_type.split("/")
    if len(parts) != 3 or parts[1] != "msg" or not parts[0] or not parts[2]:
        raise ValueError("msg_type must look like 'package/msg/Name', got %r" % (msg_type,))
    package, name = parts[0], parts[2]
    try:
        module = __import__("%s.msg" % package, fromlist=["_%s" % name])
    except ImportError as exc:
        raise ImportError(
            "ROS message package %r is not installed; cannot use %r" % (package, msg_type)
        ) from exc
    cls = getattr(module, name, None)
    if cls is None:
        raise ValueError("message class %r not found in package %r" % (name, package))
    return cls


def _fill_msg(msg, data):
    """Fill a ROS message instance from a nested dict, recursively.

    Unknown keys raise AttributeError from getattr on the message
    object; that failure surfaces to the caller rather than being
    silently dropped.
    """
    for key, value in data.items():
        current = getattr(msg, key)
        if isinstance(value, dict) and not isinstance(current, (str, bytes)):
            _fill_msg(current, value)
        else:
            setattr(msg, key, value)
    return msg


class ROS2Bridge:
    """Bridge to ROS 2 via rclpy (if available) or loopback transport."""

    def __init__(self, node_name="eosim_bridge"):
        self.node_name = node_name
        self._node = None
        self._connected = False
        self._transport = None  # "rclpy" or "loopback"
        self.publishers = {}
        self.subscribers = {}
        self._loopback_callbacks = []  # (topic, callback) for disconnect()

    def connect(self, timeout=5.0, transport="auto"):
        if transport not in ("auto", "rclpy", "loopback"):
            raise ValueError("transport must be 'auto', 'rclpy' or 'loopback'")
        if transport == "loopback":
            self._node = None
            self._connected = True
            self._transport = "loopback"
            return True
        try:
            import rclpy

            rclpy.init()
            self._node = rclpy.create_node(self.node_name)
            self._connected = True
            self._transport = "rclpy"
        except (ImportError, Exception):
            self._node = None
            self._connected = False
            self._transport = None
        return self._connected

    @property
    def transport(self):
        """'rclpy', 'loopback', or None when not connected."""
        return self._transport if self._connected else None

    def disconnect(self):
        if self._transport == "loopback":
            for topic, callback in self._loopback_callbacks:
                _loopback_unsubscribe(topic, callback)
            self._loopback_callbacks = []
        if self._node:
            self._node.destroy_node()
        try:
            import rclpy

            rclpy.shutdown()
        except Exception:
            pass
        self._node = None
        self._connected = False
        self._transport = None
        self.publishers = {}
        self.subscribers = {}

    def publish(self, topic, msg_type, data):
        if not self._connected:
            raise RuntimeError(
                "ROS2Bridge.publish: not connected; call connect() first or install rclpy"
            )
        if not topic or not msg_type:
            raise ValueError("publish requires a non-empty topic and msg_type")
        if not isinstance(data, dict):
            raise ValueError("publish data must be a dict")
        if self._transport == "rclpy":
            key = (topic, msg_type)
            if key not in self.publishers:
                cls = _resolve_msg_class(msg_type)
                pub = self._node.create_publisher(cls, topic, 10)
                self.publishers[key] = (cls, pub)
            cls, pub = self.publishers[key]
            msg = _fill_msg(cls(), data)
            pub.publish(msg)
        else:
            _loopback_publish(topic, msg_type, data)

    def subscribe(self, topic, msg_type, callback):
        if not self._connected:
            raise RuntimeError(
                "ROS2Bridge.subscribe: not connected; call connect() first or install rclpy"
            )
        if not topic or not msg_type:
            raise ValueError("subscribe requires a non-empty topic and msg_type")
        if not callable(callback):
            raise ValueError("subscribe requires a callable callback")
        if self._transport == "rclpy":
            cls = _resolve_msg_class(msg_type)

            def _ros_callback(msg, _topic=topic, _type=msg_type, _cb=callback):
                _cb(_topic, _type, msg)

            self._node.create_subscription(cls, topic, _ros_callback, 10)
            self.subscribers[topic] = callback
        else:
            _loopback_subscribe(topic, callback)
            self.subscribers[topic] = callback
            self._loopback_callbacks.append((topic, callback))
        return callback

    def unsubscribe(self, topic, callback=None):
        """Remove a loopback subscription (rclpy subscriptions cannot be
        removed through this API yet — destroying the node drops them)."""
        if self._transport == "loopback":
            callback = callback or self.subscribers.get(topic)
            if callback is not None:
                _loopback_unsubscribe(topic, callback)
                self._loopback_callbacks = [
                    pair for pair in self._loopback_callbacks if pair != (topic, callback)
                ]
            self.subscribers.pop(topic, None)

    def spin_once(self, timeout_sec=0.1):
        if self._node:
            try:
                import rclpy

                rclpy.spin_once(self._node, timeout_sec=timeout_sec)
            except Exception:
                pass
        # Loopback delivery is synchronous: nothing to spin.
