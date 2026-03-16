import sys
import uvicorn
# Import app của bạn để nó load toàn bộ các module backend
from app.main import app 

def verify_railway_readiness():
    # Danh sách các thư viện "độc hại" gây tốn RAM trên Railway
    heavy_libs = ['torch', 'transformers', 'sentence_transformers']
    
    print("\n--- ĐANG KIỂM TRA DEPENDENCIES ---")
    found = [lib for lib in heavy_libs if lib in sys.modules]
    
    if found:
        print(f"❌ CẢNH BÁO: Phát hiện {found} đã bị load vào RAM!")
        print("Đang tìm file 'thủ phạm'...")
        # Kiểm tra xem có phải do file contradictions không
        if 'app.ai.models.contradictions' in sys.modules:
            print("👉 Thủ phạm chính: file 'app.ai.models.contradictions' đang được import ở đâu đó.")
    else:
        print("✅ SẠCH SẼ: Không thấy thư viện nặng nào được load.")
        print("Bạn có thể an tâm deploy lên Railway (Option: Gemini Only).")
    print("----------------------------------\n")

if __name__ == "__main__":
    verify_railway_readiness()