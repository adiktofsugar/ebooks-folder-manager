export interface DrmAction {
  type: "drm";
}
export interface RenameAction {
  type: "rename";
}
export interface PrintAction {
  type: "print";
}
export interface PdfAction {
  type: "pdf";
}
export interface NoneAction {
  type: "none";
}
export type Action =
  | DrmAction
  | RenameAction
  | PrintAction
  | PdfAction
  | NoneAction;
