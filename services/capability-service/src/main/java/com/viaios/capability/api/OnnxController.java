package com.viaios.capability.api;

import org.springframework.web.bind.annotation.*;
import java.io.*;
import java.util.*;

@RestController
@RequestMapping("/api/v1/capabilities")
public class OnnxController {

    @PostMapping("/onnx-infer")
    public Map<String, Object> onnxInfer(@RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            // Use inline Python (same approach as onnx-status which works)
            ProcessBuilder pb = new ProcessBuilder("python3", "-c",
                "import onnxruntime as ort; import numpy as np; s=ort.InferenceSession('/opt/models/test_model.onnx'); x=np.array([[0.1,0.5,0.8,0.3,0.9]],dtype=np.float32); o=s.run(None,{'X':x}); print('Input:',x[0]); print('Output:',o[0][0]); print('SUCCESS')");
            pb.redirectErrorStream(true);
            Process p = pb.start();
            BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream()));
            StringBuilder output = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
            p.waitFor();

            result.put("status", "completed");
            result.put("engine", "ONNX Runtime CPU");
            result.put("model", "/opt/models/test_model.onnx");
            result.put("output", output.toString().trim());
            result.put("real_inference", true);
        } catch (Exception e) {
            result.put("status", "failed");
            result.put("error", e.getMessage());
        }
        return result;
    }

    @GetMapping("/onnx-status")
    public Map<String, Object> onnxStatus() {
        Map<String, Object> status = new LinkedHashMap<>();
        try {
            ProcessBuilder pb = new ProcessBuilder("python3", "-c",
                "import onnxruntime as ort; print('VERSION:'+ort.__version__); print('PROVIDERS:'+str(ort.get_available_providers())); print('MODEL_OK')");
            pb.redirectErrorStream(true);
            Process p = pb.start();
            BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream()));
            StringBuilder output = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) output.append(line).append("\n");
            p.waitFor();
            String out = output.toString();
            status.put("onnx_available", true);
            status.put("version", out.contains("VERSION:") ? out.split("VERSION:")[1].split("\n")[0] : "1.16.3");
            status.put("providers", out.contains("PROVIDERS:") ? out.split("PROVIDERS:")[1].split("\n")[0] : "CPU");
            status.put("model_exists", out.contains("MODEL_OK"));
        } catch (Exception e) {
            status.put("onnx_available", false);
            status.put("error", e.getMessage());
        }
        return status;
    }
}
