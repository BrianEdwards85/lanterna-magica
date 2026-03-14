(ns lanterna-magica.events.init
  (:require
   [lanterna-magica.components.toaster :as toaster]
   [lanterna-magica.config :as config]
   [lanterna-magica.db :as db]
   [lanterna-magica.events :as-alias events]
   [lanterna-magica.routes :as routes]
   [re-frame.core :as rf]
   [re-graph.core :as re-graph]))

(rf/reg-event-fx
  ::events/initialize-db
  (fn [_ _]
    {:db db/default-db}))

(rf/reg-fx
  :navigate
  (fn [route]
    (if (vector? route)
      (apply routes/navigate! route)
      (routes/navigate! route))))

(rf/reg-fx
  :toast
  (fn [opts]
    (toaster/show! opts)))

(rf/reg-fx
  :toaster/init
  (fn [_]
    (toaster/init!)))

(rf/reg-event-fx
  ::events/boot
  (fn [_ _]
    {:toaster/init true
     :dispatch-n   [[::re-graph/init {:ws   nil
                                      :http {:url config/GRAPHQL_URL}}]
                    [::events/fetch-dimension-types]]}))
