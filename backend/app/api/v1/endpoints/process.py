from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ....models.process import ProcessRequest, ProcessResponse
from ....services.file_service import FileService
from ....services.parser_service import ParserService
from ....core.config import settings
from pathlib import Path

router = APIRouter()


@router.post("/", response_model=ProcessResponse)
async def process_files(request: ProcessRequest):
    main_file_path = FileService.get_file_path(request.main_file_id)
    if not main_file_path:
        raise HTTPException(status_code=404, detail="Main file not found")

    csf_file_path = None
    if request.csf_file_id:
        csf_file_path = FileService.get_file_path(request.csf_file_id)
        if not csf_file_path:
            raise HTTPException(status_code=404, detail="CSF file not found")

    try:
        result = ParserService.process_files(
            main_file_path=str(main_file_path),
            csf_file_path=str(csf_file_path) if csf_file_path else None,
            language_code=request.language_code,
            country_code=request.country_code,
            output_dir=str(settings.OUTPUT_DIR)
        )

        return ProcessResponse(
            success=True,
            message="Processing completed successfully",
            output_file=Path(result["output_file"]).name,
            field_count=result["field_count"],
            processing_time=result["processing_time"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = settings.OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='text/csv'
    )