export interface InferResponse {
  input_preview_png: string
  output_preview_png: string
  uncertainty_preview_png: string
  output_geotiff: string
  input_shape: number[]
  output_shape: number[]
  input_resolution_m: number
  output_resolution_m: number
  metrics: { psnr: number; ssim: number; sam: number; ergas: number } | null
}
