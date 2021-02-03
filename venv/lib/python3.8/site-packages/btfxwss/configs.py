ERR_UNK = 10000, "Unknown error"
ERR_GENERIC = 10001, "Generic error"
ERR_CONCURRENCY = 10008, "Concurrency error"
ERR_PARAMS = 10020, "Request parameters error"
ERR_CONF_FAIL = 10050, "Configuration setup failed"
ERR_AUTH_FAIL = 10100, "Failed authentication"
ERR_AUTH_PAYLOAD = 10111, "Error in authentication request payload"
ERR_AUTH_SIG = 10112, "Error in authentication request signature"
ERR_AUTH_HMAC = 10113, "Error in authentication request encryption"
ERR_AUTH_NONCE = 10114, "Error in authentication request nonce"
ERR_UNAUTH_FAIL = 10200, "Error in un-authentication request"
ERR_SUB_FAIL = 10300, "Failed channel subscription"
ERR_SUB_MULTI = 10301, "Failed channel subscription: already subscribed"
ERR_UNSUB_FAIL = 10400, "Failed channel un-subscription: channel not found"
ERR_READY = 11000, "Not ready, try again later"
EVT_STOP = 20051, "Websocket server stopping... please reconnect later"
EVT_RESYNC_START = 20060, "Websocket server resyncing... please reconnect later"
EVT_RESYNC_STOP = 20061, "Websocket server resync complete. please reconnect"
EVT_INFO = 5000, "Info message"

auth_channels = {
    "bu: balance update",
    "ps: position snapshot",
    "pn: new position",
    "pu: position update",
    "pc: position close",
    "ws: wallet snapshot",
    "wu: wallet update",
    "os: order snapshot",
    "on: new order",
    "ou: order update",
    "oc: order cancel",
    "oc-req: order cancel request",
    "oc_multi-req: multiple orders cancel request",
    "te: trade executed",
    "tu: trade execution update",
    "fte: funding trade execution",
    "ftu: funding trade update",
    "hos: historical order snapshot",
    "mis: margin information snapshot",
    "miu: margin information update",
    "n: notification",
    "fos: funding offer snapshot",
    "fon: funding offer new",
    "fou: funding offer update",
    "foc: funding offer cancel",
    "hfos: historical funding offer snapshot",
    "fcs: funding credits snapshot",
    "fcn: funding credits new",
    "fcu: funding credits update",
    "fcc: funding credits close",
    "hfcs: historical funding credits snapshot",
    "fls: funding loan snapshot",
    "fln: funding loan new",
    "flu: funding loan update",
    "flc: funding loan close",
    "hfls: historical funding loan snapshot",
    "hfts: historical funding trade snapshot",
    "uac: user custom price alert"
}
