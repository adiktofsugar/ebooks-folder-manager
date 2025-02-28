import modLogger, { type GlobalLogger } from "js-logger";
// for some reason the types are wrong on the default export
const Logger = modLogger as unknown as GlobalLogger;
export default Logger;
