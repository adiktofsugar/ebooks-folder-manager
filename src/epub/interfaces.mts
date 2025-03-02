export interface XmlNodeValue {
  attributes?: Record<string, string>;
  "#text": string;
}

export type XmlNode = {
  [key: string]: XmlNode | XmlNode[];
} & XmlNodeValue;
