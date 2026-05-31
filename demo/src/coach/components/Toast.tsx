import React, { useEffect } from "react";
import type { BaseComponentProps } from "@json-render/react";

interface ToastProps { text: string; duration?: number; }

const Toast = ({ props, emit }: BaseComponentProps<ToastProps>) => {
  useEffect(() => {
    const t = setTimeout(() => emit("dismiss"), (props.duration ?? 4) * 1000);
    return () => clearTimeout(t);
  }, []);

  return (
    <div style={{
      background: "#333", color: "#fff", borderRadius: 8,
      padding: "10px 16px", fontSize: 14, maxWidth: 300,
      boxShadow: "0 2px 12px rgba(0,0,0,0.25)",
    }}>
      {props.text}
    </div>
  );
};

export default Toast;
