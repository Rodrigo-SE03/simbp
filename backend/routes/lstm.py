from ia.LSTM.model import load_model, create_model, predict
from fastapi import APIRouter, BackgroundTasks, Response, Query
from loguru import logger

router = APIRouter()

flag_training = False
lstm_model = None
lstm_scaler = None
lstm_le = None


def create_lstm_model():
    global lstm_model, lstm_scaler, lstm_le, flag_training
    if flag_training:
        return
    try:
        flag_training = True
        lstm_model, lstm_scaler, lstm_le = create_model()
        flag_training = False
    except Exception as e:
        flag_training = False
        logger.exception(f"Error creating model: {e}")


@router.get("/update_model")
def update_model(background_tasks: BackgroundTasks):
    background_tasks.add_task(create_lstm_model)
    return Response(status_code=200)


@router.get("")
def get_preds(background_tasks: BackgroundTasks, mac=Query(..., alias="mac")):
    global lstm_model, lstm_scaler, lstm_le, flag_training
    if flag_training:
        return Response(
            status_code=503, content="Model is training, please try again later."
        )

    if lstm_model is None:
        try:
            lstm_model, lstm_scaler, lstm_le = load_model()
        except Exception as e:
            logger.exception(f"Error loading model: {e}")
            background_tasks.add_task(create_lstm_model)
            return Response(
                status_code=503, content="Model is training, please try again later."
            )

    try:
        pred = predict(lstm_model, lstm_scaler, lstm_le, mac)
        try:
            return {"predicao": pred.tolist()}
        except Exception:
            return {"predicao": []}
    except ValueError as e:
        logger.error(f"Error in prediction: {e}")
        return Response(status_code=503, content="Not enough data for prediction.")
